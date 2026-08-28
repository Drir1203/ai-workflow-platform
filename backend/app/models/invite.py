from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class Invite(Base, TimestampMixin):
    """团队邀请：owner 生成含 code 的邀请，他人注册/登录时用 code 加入共享 tenant。

    - code 唯一索引，URL-safe 随机串，7 天过期
    - email 限受邀邮箱（注册或 accept 时校验）；expires_at 到期即失效
    - used_at 非空 = 已消费，防重复使用
    """

    __tablename__ = "invites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    email: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="member")
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    inviter_id: Mapped[str] = mapped_column(String(36))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
