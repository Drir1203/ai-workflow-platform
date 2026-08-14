from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WorkflowStep(BaseModel):
    """工作流步骤：一个 Agent 调用及其参数模板。"""

    label: str
    agent_key: str
    params: dict = Field(default_factory=dict)


class Schedule(BaseModel):
    """定时调度：cron（如 "0 9 * * 1"）或 interval_minutes 二选一。"""

    cron: str | None = None
    interval_minutes: int | None = None


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    steps: list[WorkflowStep] = Field(default_factory=list)
    schedule: Schedule | None = None


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    steps: list[WorkflowStep] | None = None
    schedule: Schedule | None = None
    enabled: bool | None = None


class WorkflowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    description: str | None
    steps: list[dict]
    schedule: dict | None
    enabled: bool
    created_at: datetime
    updated_at: datetime


class WorkflowRunCreated(BaseModel):
    run_id: str
    status: str


class WorkflowRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_id: str
    status: str
    results: list[dict] | None
    error: str | None
    triggered_by: str
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
