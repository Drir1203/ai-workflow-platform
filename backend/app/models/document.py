from uuid import uuid4

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class Document(Base, TimestampMixin):
    """知识库文档（上传或扫描导入），内容切片存于 document_chunks。"""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), default="default", index=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(20), default="upload")  # upload|scan
    content_type: Mapped[str] = mapped_column(String(20))  # md|txt|pdf|docx
    status: Mapped[str] = mapped_column(String(20), default="ready")  # ready|processing|error
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    doc_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
