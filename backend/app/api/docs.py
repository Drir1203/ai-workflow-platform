from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models.doc import Doc
from ..models.project import Project
from ..models.user import User
from ..schemas.doc import DocCreate, DocRead, DocUpdate
from .deps import get_current_user

router = APIRouter(prefix="/api/docs", tags=["docs"])


async def _get_owned_doc(db: AsyncSession, user: User, doc_id: str) -> Doc:
    """取当前租户下的文档；不存在或归属他租户一律 404，不泄露存在性（IDOR 防护）。"""
    doc = await db.get(Doc, doc_id)
    if doc is None or doc.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="doc not found")
    return doc


async def _get_owned_project(db: AsyncSession, user: User, project_id: str) -> Project:
    """校验项目属于当前租户，用于建文档时的归属约束（防串建到他人项目下）。"""
    project = await db.get(Project, project_id)
    if project is None or project.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@router.get("", response_model=list[DocRead])
async def list_docs(
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Doc]:
    # 数据隔离：仅返回当前用户租户下的文档（project_id 只是附加筛选）
    query = select(Doc).where(Doc.tenant_id == user.tenant_id).order_by(Doc.updated_at.desc())
    if project_id:
        query = query.where(Doc.project_id == project_id)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=DocRead, status_code=status.HTTP_201_CREATED)
async def create_doc(
    payload: DocCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Doc:
    await _get_owned_project(db, user, payload.project_id)
    # 归属：租户随创建者注入，隔离不落空
    doc = Doc(**payload.model_dump(), tenant_id=user.tenant_id)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("/{doc_id}", response_model=DocRead)
async def get_doc(
    doc_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> Doc:
    return await _get_owned_doc(db, user, doc_id)


@router.patch("/{doc_id}", response_model=DocRead)
async def update_doc(
    doc_id: str,
    payload: DocUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Doc:
    doc = await _get_owned_doc(db, user, doc_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(doc, field, value)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doc(
    doc_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    doc = await _get_owned_doc(db, user, doc_id)
    await db.delete(doc)
    await db.commit()
