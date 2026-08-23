from dataclasses import asdict
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..agents.custom import CustomAgentExecutor, resolve_agent, validate_params
from ..agents.registry import AGENT_REGISTRY, ensure_registered
from ..agents.runner import agent_run_manager
from ..config import settings
from ..core.ratelimit import rate_limit
from ..db import get_db
from ..models.agent_run import AgentRun
from ..models.custom_agent import CustomAgent
from ..models.project import Project
from ..models.user import User
from ..schemas.agent import (
    AgentInfo,
    AgentParamInfo,
    AgentRunCreated,
    AgentRunRead,
    AgentRunRequest,
    CustomAgentCreate,
    CustomAgentRead,
    CustomAgentUpdate,
    Paginated,
)
from .deps import get_current_user

router = APIRouter(prefix="/api/agents", tags=["agents"])

# 限流依赖：按「来源 IP + agent_run」滑动窗口计数，超限抛 429（Agent 触发防误触）。
# 端点的 `_rl: None = Depends(...)` 参数不传值，只负责把依赖挂进请求链路，见 core/ratelimit.py
_run_limit = rate_limit(settings.ratelimit_run_per_min, 60, scope="agent_run")


async def _get_custom_or_404(db: AsyncSession, key: str, user: User) -> CustomAgent:
    """按 key 取当前用户的自定义 Agent，否则 404（防止越权访问他人 Agent）。"""
    result = await db.execute(
        select(CustomAgent).where(CustomAgent.key == key, CustomAgent.user_id == user.id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="custom agent not found")
    return agent


@router.get("", response_model=list[AgentInfo])
async def list_agents(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AgentInfo]:
    """内置（registry）与自定义（DB）Agent 合并列表，source 字段区分来源。"""
    ensure_registered()
    builtin = [
        AgentInfo(
            key=a.key,
            name=a.name,
            description=a.description,
            param_schema=[AgentParamInfo(**asdict(p)) for p in a.param_schema],
            source="builtin",
        )
        for a in AGENT_REGISTRY.list()
    ]
    result = await db.execute(
        select(CustomAgent).where(CustomAgent.tenant_id == user.tenant_id)
    )
    custom = [
        AgentInfo(
            key=a.key,
            name=a.name,
            description=a.description or "",
            param_schema=a.param_schema,
            source="custom",
            prompt=a.prompt,
        )
        for a in result.scalars().all()
    ]
    return builtin + custom


@router.post("", response_model=CustomAgentRead, status_code=status.HTTP_201_CREATED)
async def create_custom_agent(
    payload: CustomAgentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CustomAgent:
    """创建自定义 Agent：key 自动生成 custom-<hex8> 并查重，全局唯一。"""
    for _ in range(5):
        key = f"custom-{uuid4().hex[:8]}"
        exists = await db.execute(select(CustomAgent).where(CustomAgent.key == key))
        if exists.scalar_one_or_none() is not None:
            continue  # 极小概率撞 key，换一个重试
        agent = CustomAgent(
            tenant_id=user.tenant_id,
            user_id=user.id,
            key=key,
            name=payload.name,
            description=payload.description,
            prompt=payload.prompt,
            param_schema=[p.model_dump() for p in payload.param_schema],
        )
        db.add(agent)
        try:
            await db.commit()
        except IntegrityError:
            # 并发下两个请求可能同 key：唯一索引冲突，回滚后换 key 重试
            await db.rollback()
            continue
        await db.refresh(agent)
        return agent
    # 连续 5 次撞 key（概率极低）兜底报错，避免 500
    raise HTTPException(status_code=409, detail="创建失败，请重试")


@router.patch("/{agent_key}", response_model=CustomAgentRead)
async def update_custom_agent(
    agent_key: str,
    payload: CustomAgentUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CustomAgent:
    """更新自定义 Agent（仅本人）：None 字段不修改。"""
    agent = await _get_custom_or_404(db, agent_key, user)
    if payload.name is not None:
        agent.name = payload.name
    if payload.description is not None:
        agent.description = payload.description
    if payload.prompt is not None:
        agent.prompt = payload.prompt
    if payload.param_schema is not None:
        agent.param_schema = [p.model_dump() for p in payload.param_schema]
    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/{agent_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_agent(
    agent_key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """删除自定义 Agent（仅本人）。"""
    agent = await _get_custom_or_404(db, agent_key, user)
    await db.delete(agent)
    await db.commit()


@router.get("/runs", response_model=Paginated[AgentRunRead])
async def list_runs(
    project_id: str | None = None,
    agent_key: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Paginated[AgentRunRead]:
    # 数据隔离 R17：运行记录按租户可见（团队共享模型，与 workflows 一致）
    where = [AgentRun.tenant_id == user.tenant_id]
    if project_id:
        where.append(AgentRun.project_id == project_id)
    if agent_key:
        where.append(AgentRun.agent_key == agent_key)

    total = (
        await db.execute(select(func.count()).select_from(AgentRun).where(*where))
    ).scalar_one()
    result = await db.execute(
        select(AgentRun)
        .where(*where)
        .order_by(AgentRun.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(result.scalars().all())
    return Paginated(items=items, total=total, page=page, page_size=page_size)


@router.get("/runs/{run_id}", response_model=AgentRunRead)
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentRun:
    run = await db.get(AgentRun, run_id)
    if run is None or run.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.post(
    "/{agent_key}/run",
    response_model=AgentRunCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_agent(
    agent_key: str,
    payload: AgentRunRequest,
    _rl: None = Depends(_run_limit),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentRunCreated:
    ensure_registered()
    # 内置 + 自定义 Agent 统一解析；后台执行（runner）也有同样兜底
    agent = await resolve_agent(db, agent_key)
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    # 自定义 Agent 仅限同租户执行（与 list_agents 可见范围一致），防跨租户猜 key 调用；
    # 同租户其他用户可运行（团队共享模型，Agent 本身对租户内可见）
    if isinstance(agent, CustomAgentExecutor) and agent.agent.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="agent not found")
    # 自定义 Agent 提交时即校验必填参数，避免无效请求白白排队
    if agent_key.startswith("custom-"):
        try:
            validate_params(agent.param_schema, payload.params)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    project_id = payload.project_id
    if project_id:
        # 数据隔离 R17：项目必须属于当前租户，防跨租户把 run 挂到他人项目下
        project = await db.get(Project, project_id)
        if project is None or project.tenant_id != user.tenant_id:
            raise HTTPException(status_code=404, detail="project not found")

    run = AgentRun(
        user_id=user.id,
        tenant_id=user.tenant_id,
        agent_key=agent_key,
        status="pending",
        params=payload.params,
        project_id=project_id,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    agent_run_manager.submit(run.id)
    return AgentRunCreated(run_id=run.id, status=run.status)
