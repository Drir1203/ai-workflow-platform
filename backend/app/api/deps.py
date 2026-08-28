from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import decode_access_token
from ..db import get_db
from ..models.invite import Invite
from ..models.user import User

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")
    return user


def require_role(*roles: str):
    """依赖工厂：要求当前用户租户角色 ∈ roles，否则 403。

    用于把 readonly 挡在各实体写端点外（create/update/delete）；
    list/read 端点不挂此依赖，保持只读可见。
    """
    async def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient permissions")
        return user

    return _checker


# 团队 owner 专属操作（发邀请 / 改角色 / 移除成员）统一复用
owner_only = require_role("owner")


async def resolve_invite(db: AsyncSession, code: str, email: str) -> Invite | None:
    """按 code 取未消费邀请并校验未过期、受邀邮箱一致；任一不满足返回 None。

    SQLite 读回 DateTime 可能丢失时区，比较前补 tzinfo，避免与 tz-aware 的 now 比较抛 TypeError。
    """
    result = await db.execute(
        select(Invite).where(Invite.code == code, Invite.used_at.is_(None))
    )
    invite = result.scalar_one_or_none()
    if invite is None:
        return None
    expires = invite.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc) or invite.email.lower() != email.lower():
        return None
    return invite
