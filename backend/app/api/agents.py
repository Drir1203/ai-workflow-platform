from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..agents.registry import AGENT_REGISTRY, ensure_registered
from ..agents.runner import agent_run_manager
from ..db import get_db
from ..models.agent_run import AgentRun
from ..models.project import Project
from ..models.user import User
from ..schemas.agent import (
    AgentInfo,
    AgentParamInfo,
    AgentRunCreated,
    AgentRunRead,
    AgentRunRequest,
    Paginated,
)
from .deps import get_current_user

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("", response_model=list[AgentInfo])
async def list_agents(_user: User = Depends(get_current_user)) -> list[AgentInfo]:
    ensure_registered()
    return [
        AgentInfo(
            key=a.key,
            name=a.name,
            description=a.description,
            param_schema=[AgentParamInfo(**asdict(p)) for p in a.param_schema],
        )
        for a in AGENT_REGISTRY.list()
    ]


@router.get("/runs", response_model=Paginated[AgentRunRead])
async def list_runs(
    project_id: str | None = None,
    agent_key: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Paginated[AgentRunRead]:
    where = [AgentRun.user_id == user.id]
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
    if run is None or run.user_id != user.id:
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
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentRunCreated:
    ensure_registered()
    if AGENT_REGISTRY.get(agent_key) is None:
        raise HTTPException(status_code=404, detail="agent not found")

    project_id = payload.project_id
    if project_id:
        project = await db.get(Project, project_id)
        if project is None:
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
