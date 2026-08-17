from uuid import uuid4

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class ParamTemplate(Base, TimestampMixin):
    """参数预置模板：把一组参数值存成命名模板，运行 Agent/编辑工作流步骤时一键复用。

    agent_key 绑定该模板适用于哪个智能体；params 是参数值字典（与 run 请求同结构）。
    """

    __tablename__ = "param_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), default="default", index=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    agent_key: Mapped[str] = mapped_column(String(80), index=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
