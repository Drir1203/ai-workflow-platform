from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    source: str  # upload|scan
    content_type: str  # md|txt|pdf|docx
    status: str  # ready|processing|error
    error: str | None
    source_path: str | None
    created_at: datetime


class KnowledgeQuery(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class KnowledgeSource(BaseModel):
    document_id: str
    document_name: str
    seq: int
    content: str
    matched: list[str] = Field(default_factory=list)


class KnowledgeResponse(BaseModel):
    answer: str
    sources: list[KnowledgeSource] = Field(default_factory=list)


class ScanResult(BaseModel):
    imported: int
    skipped: list[str] = Field(default_factory=list)
