from uuid import uuid4

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class CustomAgent(Base, TimestampMixin):
    """用户自定义 Agent：param_schema + prompt 存库，与内置 Agent 并存可运行。

    key 形如 `custom-<hex8>`，全局唯一；prompt 支持 {{param}} 占位符，
    运行时由 CustomAgentExecutor 用参数值替换后调 AI 引擎。
    """

    __tablename__ = "custom_agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), default="default", index=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt: Mapped[str] = mapped_column(Text)
    param_schema: Mapped[list] = mapped_column(JSON, default=list)
