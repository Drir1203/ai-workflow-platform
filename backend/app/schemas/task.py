from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

PRIORITIES = "^(low|medium|high)$"
STATUSES = "^(todo|in_progress|done)$"


class TaskCreate(BaseModel):
    project_id: str
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    priority: str = Field(default="medium", pattern=PRIORITIES)
    status: str = Field(default="todo", pattern=STATUSES)
    due_date: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    priority: str | None = Field(default=None, pattern=PRIORITIES)
    status: str | None = Field(default=None, pattern=STATUSES)
    due_date: date | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    title: str
    description: str | None
    priority: str
    status: str
    due_date: date | None
    created_at: datetime
    updated_at: datetime
