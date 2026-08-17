from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..core.ratelimit import rate_limit
from ..core.security import create_access_token, hash_password, verify_password
from ..db import get_db
from ..models.user import User
from ..schemas.user import LoginRequest, RegisterRequest, TokenResponse, UserRead

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
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
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
