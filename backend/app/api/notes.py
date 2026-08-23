from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models.note import Note
from ..models.project import Project
from ..models.user import User
from ..schemas.note import NoteCreate, NoteRead, NoteUpdate
from .deps import get_current_user

router = APIRouter(prefix="/api/notes", tags=["notes"])


async def _get_owned_note(db: AsyncSession, user: User, note_id: str) -> Note:
    """取当前租户下的笔记；不存在或归属他租户一律 404，不泄露存在性（IDOR 防护）。"""
    note = await db.get(Note, note_id)
    if note is None or note.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="note not found")
    return note


async def _get_owned_project(db: AsyncSession, user: User, project_id: str) -> Project:
    """校验项目属于当前租户，用于建笔记时的归属约束（防串建到他人项目下）。"""
    project = await db.get(Project, project_id)
    if project is None or project.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@router.get("", response_model=list[NoteRead])
async def list_notes(
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Note]:
    # 数据隔离 R17：仅返回当前用户租户下的笔记（project_id 只是附加筛选）
    query = select(Note).where(Note.tenant_id == user.tenant_id).order_by(Note.updated_at.desc())
    if project_id:
        query = query.where(Note.project_id == project_id)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: NoteCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Note:
    await _get_owned_project(db, user, payload.project_id)
    # 归属：租户随创建者注入，隔离不落空
    note = Note(**payload.model_dump(), tenant_id=user.tenant_id)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


@router.get("/{note_id}", response_model=NoteRead)
async def get_note(
    note_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> Note:
    return await _get_owned_note(db, user, note_id)


@router.patch("/{note_id}", response_model=NoteRead)
async def update_note(
    note_id: str,
    payload: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Note:
    note = await _get_owned_note(db, user, note_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    await db.commit()
    await db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    note = await _get_owned_note(db, user, note_id)
    await db.delete(note)
    await db.commit()
