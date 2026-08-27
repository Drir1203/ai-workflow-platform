from uuid import uuid4

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class Doc(Base, TimestampMixin):
    """Markdown 文档（与速记笔记 notes 区分：文档是正式产物，可预览渲染）。

    类名取 Doc 而非 Document，避免与知识库已存在的 Document 模型冲突。
    """

    __tablename__ = "docs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), default="default", index=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text, default="")  # Markdown 源码
    doc_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 预留：标签/固定版本等
