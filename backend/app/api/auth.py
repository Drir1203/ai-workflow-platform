from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..core.ratelimit import rate_limit
from ..core.security import create_access_token, hash_password, verify_password
from ..db import get_db
from ..models.user import User
from ..schemas.user import LoginRequest, RegisterRequest, TokenResponse, UserRead
from ..services.guest import ensure_guest
from .deps import resolve_invite

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 限流依赖：按「来源 IP + auth」滑动窗口计数，超限抛 429（登录/注册防爆破）。
# 端点的 `_rl: None = Depends(...)` 参数不传值，只负责把该依赖挂进请求链路，见 core/ratelimit.py
_auth_limit = rate_limit(settings.ratelimit_auth_per_min, 60, scope="auth")


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    _rl: None = Depends(_auth_limit),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered")
    # 每用户默认分配独立私有租户（数据隔离 R17）：用户注册后其全部数据
    # 挂在独有 tenant_id 下，projects/tasks/notes 等按该值过滤，天然互不可见。
    # 携带团队邀请码时改为进入邀请方的共享租户并继承其角色（团队共享能力入口）。
    tenant_id, role = str(uuid4()), "owner"
    if payload.invite_code:
        invite = await resolve_invite(db, payload.invite_code, payload.email)
        if invite is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邀请码无效或已过期")
        tenant_id, role = invite.tenant_id, invite.role
        invite.used_at = datetime.now(timezone.utc)
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        tenant_id=tenant_id,
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return TokenResponse(
        access_token=create_access_token(user.id), user=UserRead.model_validate(user)
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    _rl: None = Depends(_auth_limit),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid email or password")
    return TokenResponse(
        access_token=create_access_token(user.id), user=UserRead.model_validate(user)
    )


@router.post("/guest", response_model=TokenResponse)
async def guest_login(
    _rl: None = Depends(_auth_limit),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """访客体验入口：免注册换取共享演示租户的 token。

    与 login 共用同一个 auth 限流桶（同 IP 每分钟上限），避免被拿来刷账号创建。
    """
    if not settings.guest_access_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="访客入口已关闭")
    user = await ensure_guest(db)
    return TokenResponse(
        access_token=create_access_token(user.id), user=UserRead.model_validate(user)
    )
