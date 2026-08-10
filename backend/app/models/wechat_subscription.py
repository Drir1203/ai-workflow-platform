from uuid import uuid4

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class WechatSubscription(Base, TimestampMixin):
    """用户对某任务的微信订阅消息绑定（一次性，发送后标记 sent）。"""

    __tablename__ = "wechat_subscriptions"
    __table_args__ = (UniqueConstraint("user_id", "task_id", name="uq_wechat_sub_user_task"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), default="default", index=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    openid: Mapped[str] = mapped_column(String(64))
    template_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="subscribed")
