from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    color: str | None = None
    repo_url: str | None = None
    deploy_url: str | None = None
    local_path: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    color: str | None = None
    repo_url: str | None = None
    deploy_url: str | None = None
    local_path: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    status: str
    color: str | None
    repo_url: str | None
    deploy_url: str | None
    local_path: str | None
    created_at: datetime
    updated_at: datetime
