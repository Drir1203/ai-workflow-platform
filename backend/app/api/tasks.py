from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models.project import Project
from ..models.task import Task
from ..models.user import User
from ..schemas.task import TaskCreate, TaskRead, TaskUpdate
from .deps import get_current_user

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


async def _get_owned_task(db: AsyncSession, user: User, task_id: str) -> Task:
    """取当前租户下的任务；不存在或归属他租户一律 404，不泄露存在性（IDOR 防护）。"""
    task = await db.get(Task, task_id)
    if task is None or task.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="task not found")
    return task


async def _get_owned_project(db: AsyncSession, user: User, project_id: str) -> Project:
    """校验项目属于当前租户，用于建任务时的归属约束（防串建到他人项目下）。"""
    project = await db.get(Project, project_id)
    if project is None or project.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@router.get("", response_model=list[TaskRead])
async def list_tasks(
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Task]:
    # 数据隔离 R17：仅返回当前用户租户下的任务（project_id 只是附加筛选，不做跨租户依据）
    query = select(Task).where(Task.tenant_id == user.tenant_id).order_by(Task.created_at.desc())
    if project_id:
        query = query.where(Task.project_id == project_id)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Task:
    await _get_owned_project(db, user, payload.project_id)
    # 归属：租户随创建者注入，隔离不落空
    task = Task(**payload.model_dump(), tenant_id=user.tenant_id)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> Task:
    return await _get_owned_task(db, user, task_id)


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: str,
    payload: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Task:
    task = await _get_owned_task(db, user, task_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    task = await _get_owned_task(db, user, task_id)
    await db.delete(task)
    await db.commit()
