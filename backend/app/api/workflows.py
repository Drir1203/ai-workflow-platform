from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..agents.registry import AGENT_REGISTRY, ensure_registered
from ..config import settings
from ..core.ratelimit import rate_limit
from ..db import get_db
from ..models.custom_agent import CustomAgent
from ..models.user import User
from ..models.workflow import Workflow
from ..models.workflow_run import WorkflowRun
from ..schemas.agent import Paginated
from ..schemas.workflow import (
    WorkflowCreate,
    WorkflowRead,
    WorkflowRunCreated,
    WorkflowRunRead,
    WorkflowUpdate,
)
from ..workflows.executor import workflow_run_manager
from ..workflows.scheduler import workflow_scheduler
from .deps import get_current_user, require_role

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

# 限流依赖：按「来源 IP + workflow_run」滑动窗口计数，超限抛 429（工作流触发防误触）。
# 端点的 `_rl: None = Depends(...)` 参数不传值，只负责把依赖挂进请求链路，见 core/ratelimit.py
_run_limit = rate_limit(settings.ratelimit_run_per_min, 60, scope="workflow_run")


def _normalize_schedule(schedule) -> dict | None:
    """只保留显式设置的调度字段（cron 或 interval_minutes）。"""
    if schedule is None:
        return None
    return {k: v for k, v in schedule.model_dump().items() if v is not None}


async def _validate_steps(db: AsyncSession, user: User, steps: list[dict]) -> None:
    """校验步骤引用的 Agent：内置注册表优先，其次当前租户的自定义 Agent。"""
    ensure_registered()
    for step in steps:
        key = step.get("agent_key")
        if AGENT_REGISTRY.get(key) is not None:
            continue
        # 自定义 Agent 按租户校验（与 list_agents 可见范围一致）
        result = await db.execute(
            select(CustomAgent).where(
                CustomAgent.key == key, CustomAgent.tenant_id == user.tenant_id
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=422, detail=f"unknown agent: {key}")


@router.get("", response_model=list[WorkflowRead])
async def list_workflows(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Workflow]:
    # 数据隔离 R17：列表按租户可见（团队共享模型，与 agents.py list_agents 一致）
    result = await db.execute(
        select(Workflow)
        .where(Workflow.tenant_id == user.tenant_id)
        .order_by(Workflow.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("owner", "member")),
) -> Workflow:
    await _validate_steps(db, user, [s.model_dump() for s in payload.steps])
    wf = Workflow(
        user_id=user.id,
        tenant_id=user.tenant_id,
        name=payload.name,
        description=payload.description,
        # exclude_none: 无 node_id/position 的旧式步骤不落 null 噪音，保持存量数据干净
        steps=[s.model_dump(exclude_none=True) for s in payload.steps],
        schedule=_normalize_schedule(payload.schedule),
    )
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    workflow_scheduler.reschedule(wf)
    return wf


@router.get("/runs", response_model=Paginated[WorkflowRunRead])
async def list_workflow_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Paginated[WorkflowRunRead]:
    # 数据隔离 R17：运行记录按租户可见（团队共享模型）
    where = [WorkflowRun.tenant_id == user.tenant_id]
    total = (
        await db.execute(select(func.count()).select_from(WorkflowRun).where(*where))
    ).scalar_one()
    result = await db.execute(
        select(WorkflowRun)
        .where(*where)
        .order_by(WorkflowRun.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return Paginated(
        items=list(result.scalars().all()), total=total, page=page, page_size=page_size
    )


@router.get("/runs/{run_id}", response_model=WorkflowRunRead)
async def get_workflow_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorkflowRun:
    run = await db.get(WorkflowRun, run_id)
    if run is None or run.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.get("/{workflow_id}", response_model=WorkflowRead)
async def get_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Workflow:
    # 数据隔离 R17：查看按租户共享（团队共享模型）
    wf = await db.get(Workflow, workflow_id)
    if wf is None or wf.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="workflow not found")
    return wf


@router.patch("/{workflow_id}", response_model=WorkflowRead)
async def update_workflow(
    workflow_id: str,
    payload: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("owner", "member")),
) -> Workflow:
    # 数据隔离 R17：编辑仅创建者本人（与 agents.py update_custom_agent 一致）
    wf = await db.get(Workflow, workflow_id)
    if wf is None or wf.user_id != user.id:
        raise HTTPException(status_code=404, detail="workflow not found")

    data = payload.model_dump(exclude_unset=True)
    if "steps" in data:
        await _validate_steps(db, user, data["steps"])
        # 与 create 一致：无 node_id/position 的旧式步骤不落 null 噪音
        data["steps"] = [
            {k: v for k, v in s.items() if v is not None} for s in data["steps"]
        ]
    if "schedule" in data:
        sched = data["schedule"]
        data["schedule"] = (
            {k: v for k, v in sched.items() if v is not None} if sched else None
        )
    for field, value in data.items():
        setattr(wf, field, value)
    await db.commit()
    await db.refresh(wf)
    workflow_scheduler.reschedule(wf)
    return wf


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("owner", "member")),
) -> None:
    # 数据隔离 R17：删除仅创建者本人
    wf = await db.get(Workflow, workflow_id)
    if wf is None or wf.user_id != user.id:
        raise HTTPException(status_code=404, detail="workflow not found")
    workflow_scheduler.remove(wf.id)
    await db.delete(wf)
    await db.commit()


@router.post(
    "/{workflow_id}/run",
    response_model=WorkflowRunCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_workflow(
    workflow_id: str,
    _rl: None = Depends(_run_limit),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("owner", "member")),
) -> WorkflowRunCreated:
    # 数据隔离 R17：运行按租户共享（同租户可触发，与 agents.py run_agent 一致）
    wf = await db.get(Workflow, workflow_id)
    if wf is None or wf.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="workflow not found")
    run = WorkflowRun(
        tenant_id=wf.tenant_id,
        workflow_id=wf.id,
        user_id=user.id,
        status="pending",
        triggered_by="manual",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    workflow_run_manager.submit(run.id)
    return WorkflowRunCreated(run_id=run.id, status=run.status)
