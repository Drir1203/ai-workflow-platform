from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models.invite import Invite
from ..models.user import User
from ..schemas.team import AcceptInvite, InviteCreate, MemberUpdate, TeamMember
from ..schemas.user import UserRead
from ..services.notification import create_notification
from .deps import get_current_user, owner_only, resolve_invite

router = APIRouter(prefix="/api/team", tags=["team"])


@router.get("/members", response_model=list[TeamMember])
async def list_members(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[User]:
    """当前租户下所有成员（含自己）。共享 tenant_id 即同团队。"""
    result = await db.execute(
        select(User).where(User.tenant_id == user.tenant_id).order_by(User.created_at.asc())
    )
    return list(result.scalars().all())


@router.post("/invites", status_code=status.HTTP_201_CREATED)
async def create_invite(
    payload: InviteCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(owner_only),
) -> dict:
    """owner 生成邀请码：受邀人注册/接受后加入本租户并继承 invited role。7 天有效。"""
    invite = Invite(
        tenant_id=user.tenant_id,
        email=payload.email,
        role=payload.role,
        code=token_urlsafe(16),
        inviter_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    # invite_url 为前端注册页相对路径，复制时由前端拼 origin
    return {
        "code": invite.code,
        "email": invite.email,
        "role": invite.role,
        "expires_at": invite.expires_at,
        "invite_url": f"/register?invite_code={invite.code}",
    }


@router.post("/invites/accept", response_model=UserRead)
async def accept_invite(
    payload: AcceptInvite,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> User:
    """已登录用户凭 code 加入团队：校验受邀邮箱一致后迁入共享租户并继承角色。"""
    invite = await resolve_invite(db, payload.code, user.email)
    if invite is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邀请码无效或已过期")
    user.tenant_id = invite.tenant_id
    user.role = invite.role
    invite.used_at = datetime.now(timezone.utc)
    # 通知邀请人新成员加入（与成员迁移同一事务，通知失败不影响入团）
    await create_notification(
        db,
        user_id=invite.inviter_id,
        type="team",
        title="新成员加入团队",
        body=f"{user.email} 通过邀请加入了你的团队（角色：{invite.role}）",
        ref_id=user.id,
        tenant_id=invite.tenant_id,
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/members/{user_id}", response_model=TeamMember)
async def update_member_role(
    user_id: str,
    payload: MemberUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(owner_only),
) -> User:
    """owner 改成员角色；不可改自己；目标必须同租户（IDOR → 404）。"""
    if user_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能修改自己的角色")
    member = await db.get(User, user_id)
    if member is None or member.tenant_id != user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="member not found")
    member.role = payload.role
    # 通知被改角色者（角色变更与通知同一事务）
    await create_notification(
        db,
        user_id=member.id,
        type="team",
        title="你的团队角色已变更",
        body=f"管理员将你的角色调整为「{payload.role}」",
        tenant_id=member.tenant_id,
    )
    await db.commit()
    await db.refresh(member)
    return member


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(owner_only),
) -> None:
    """owner 移除成员 = 将其迁出共享租户（新私有租户 + role 复位 owner）；原团队数据留在原租户不可见。"""
    if user_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能移除自己")
    member = await db.get(User, user_id)
    if member is None or member.tenant_id != user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="member not found")
    old_tenant_id = member.tenant_id  # 先捕获旧租户再迁移，通知记录原团队归属
    member.tenant_id = str(uuid4())
    member.role = "owner"
    # 通知被移除者（查询靠 user_id，不受租户迁移影响）
    await create_notification(
        db,
        user_id=member.id,
        type="team",
        title="你已被移出团队",
        body="你已被管理员移出团队，原团队数据对你不再可见",
        tenant_id=old_tenant_id,
    )
    await db.commit()
