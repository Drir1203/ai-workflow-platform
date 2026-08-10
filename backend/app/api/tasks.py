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


@router.get("", response_model=list[TaskRead])
async def list_tasks(
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[Task]:
    query = select(Task).order_by(Task.created_at.desc())
    if project_id:
        query = query.where(Task.project_id == project_id)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Task:
    project = await db.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    task = Task(**payload.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: str, db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)
) -> Task:
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: str,
    payload: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Task:
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str, db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)
) -> None:
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    await db.delete(task)
    await db.commit()
