"""参数预置模板 API：命名参数值模板 CRUD，运行 Agent / 编辑工作流步骤时一键复用。"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models.param_template import ParamTemplate
from ..models.user import User
from ..schemas.template import TemplateCreate, TemplateRead, TemplateUpdate
from .deps import get_current_user, require_role

router = APIRouter(prefix="/api/param-templates", tags=["param-templates"])


async def _get_or_404(db: AsyncSession, template_id: str, user: User) -> ParamTemplate:
    """按 id 取当前用户的模板，否则 404（防止越权访问他人模板）。"""
    result = await db.execute(
        select(ParamTemplate).where(
            ParamTemplate.id == template_id, ParamTemplate.user_id == user.id
        )
    )
    tpl = result.scalar_one_or_none()
    if tpl is None:
        raise HTTPException(status_code=404, detail="template not found")
    return tpl


@router.get("", response_model=list[TemplateRead])
async def list_templates(
    agent_key: str | None = Query(None, max_length=80),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ParamTemplate]:
    """当前用户的模板列表，可按 agent_key 过滤。"""
    stmt = select(ParamTemplate).where(ParamTemplate.user_id == user.id)
    if agent_key:
        stmt = stmt.where(ParamTemplate.agent_key == agent_key)
    stmt = stmt.order_by(ParamTemplate.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("owner", "member")),
) -> ParamTemplate:
    tpl = ParamTemplate(
        tenant_id=user.tenant_id,
        user_id=user.id,
        name=payload.name,
        agent_key=payload.agent_key,
        params=payload.params,
    )
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return tpl


@router.patch("/{template_id}", response_model=TemplateRead)
async def update_template(
    template_id: str,
    payload: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("owner", "member")),
) -> ParamTemplate:
    """更新模板（仅本人）：None 字段不修改。"""
    tpl = await _get_or_404(db, template_id, user)
    if payload.name is not None:
        tpl.name = payload.name
    if payload.params is not None:
        tpl.params = payload.params
    await db.commit()
    await db.refresh(tpl)
    return tpl


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("owner", "member")),
) -> None:
    """删除模板（仅本人）。"""
    tpl = await _get_or_404(db, template_id, user)
    await db.delete(tpl)
    await db.commit()
