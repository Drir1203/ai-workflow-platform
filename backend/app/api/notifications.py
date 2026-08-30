"""站内通知中心路由：用户级收件箱。

所有端点只操作「当前用户自己的通知」（where 始终带 user_id 归属校验），
因此统一挂 get_current_user，不挂 require_role——readonly 成员同样能看自己的
通知；归属校验失败一律 404（不泄露其他用户的通知是否存在）。
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.notification import Notification
from ..models.user import User
from ..schemas.agent import Paginated
from ..schemas.notification import NotificationRead, ReadAllResult, UnreadCount
from .deps import get_current_user, get_db

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=Paginated[NotificationRead])
async def list_notifications(
    unread_only: bool = False,
    type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Paginated[NotificationRead]:
    """分页列表：限定当前用户，按创建时间倒序。支持只看未读 / 按类型过滤。"""
    where = [Notification.user_id == user.id]
    if unread_only:
        where.append(Notification.read_at.is_(None))
    if type:
        where.append(Notification.type == type)

    total = (
        await db.execute(select(func.count()).select_from(Notification).where(*where))
    ).scalar_one()
    result = await db.execute(
        select(Notification)
        .where(*where)
        .order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(result.scalars().all())
    return Paginated(items=items, total=total, page=page, page_size=page_size)


@router.get("/unread-count", response_model=UnreadCount)
async def unread_count(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UnreadCount:
    """未读数：前端铃铛红点轮询用。"""
    count = (
        await db.execute(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        )
    ).scalar_one()
    return UnreadCount(count=count)


@router.post("/read-all", response_model=ReadAllResult)
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ReadAllResult:
    """一键全部已读，返回本次更新的行数。"""
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return ReadAllResult(updated=result.rowcount or 0)


@router.post("/{notification_id}/read", status_code=204)
async def mark_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """标记单条已读：id + user_id 双重归属校验，非本人通知 404。重复标记幂等。"""
    notification = (
        await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if notification is None:
        raise HTTPException(status_code=404, detail="通知不存在")
    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
        await db.commit()


@router.delete("/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """删除单条通知：同样按 id + user_id 归属校验。"""
    notification = (
        await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if notification is None:
        raise HTTPException(status_code=404, detail="通知不存在")
    await db.delete(notification)
    await db.commit()
