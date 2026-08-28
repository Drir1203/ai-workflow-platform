from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models.doc import Doc
from ..models.project import Project
from ..models.user import User
from ..schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from .deps import get_current_user, require_role

router = APIRouter(prefix="/api/projects", tags=["projects"])


async def _get_owned_project(db: AsyncSession, user: User, project_id: str) -> Project:
    """取当前租户下的项目；不存在或归属他租户一律 404，不泄露存在性（IDOR 防护）。"""
    project = await db.get(Project, project_id)
    if project is None or project.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Project]:
    # 数据隔离 R17：仅返回当前用户租户下的项目，杜绝跨用户串读
    result = await db.execute(
        select(Project).where(Project.tenant_id == user.tenant_id).order_by(Project.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate, db: AsyncSession = Depends(get_db), user: User = Depends(require_role("owner", "member"))
) -> Project:
    # 归属：租户随创建者注入，避免落到默认 "default" 租户导致隔离失效
    project = Project(**payload.model_dump(), tenant_id=user.tenant_id)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> Project:
    return await _get_owned_project(db, user, project_id)


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("owner", "member")),
) -> Project:
    project = await _get_owned_project(db, user, project_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(require_role("owner", "member"))
) -> None:
    project = await _get_owned_project(db, user, project_id)
    # SQLite 不强制外键级联，应用层显式清理文档，防孤儿数据（tasks/notes 级联后做）
    await db.execute(delete(Doc).where(Doc.project_id == project_id))
    await db.delete(project)
    await db.commit()
