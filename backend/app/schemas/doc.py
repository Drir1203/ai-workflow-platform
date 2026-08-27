from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocCreate(BaseModel):
    project_id: str
    title: str = Field(min_length=1, max_length=200)
    content: str = ""
    doc_meta: dict | None = None


class DocUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = None
    doc_meta: dict | None = None


class DocRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    title: str
    content: str
    doc_meta: dict | None = None
    created_at: datetime
    updated_at: datetime
