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


@router.get("", response_model=list[NoteRead])
async def list_notes(
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[Note]:
    query = select(Note).order_by(Note.updated_at.desc())
    if project_id:
        query = query.where(Note.project_id == project_id)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: NoteCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Note:
    project = await db.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    note = Note(**payload.model_dump())
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


@router.get("/{note_id}", response_model=NoteRead)
async def get_note(
    note_id: str, db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)
) -> Note:
    note = await db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="note not found")
    return note


@router.patch("/{note_id}", response_model=NoteRead)
async def update_note(
    note_id: str,
    payload: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Note:
    note = await db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="note not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    await db.commit()
    await db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str, db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)
) -> None:
    note = await db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="note not found")
    await db.delete(note)
    await db.commit()
