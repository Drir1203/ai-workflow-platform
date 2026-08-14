from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Paginated(BaseModel, Generic[T]):
    """分页信封：items + 元数据。"""

    items: list[T]
    total: int
    page: int
    page_size: int


class AgentParamInfo(BaseModel):
    name: str
    label: str
    type: str
    required: bool
    default: object | None = None
    options: list[dict[str, str]] = Field(default_factory=list)
    placeholder: str = ""


class AgentInfo(BaseModel):
    key: str
    name: str
    description: str
    param_schema: list[AgentParamInfo]


class AgentRunRequest(BaseModel):
    params: dict = Field(default_factory=dict)
    project_id: str | None = None


class AgentRunCreated(BaseModel):
    run_id: str
    status: str


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_key: str
    project_id: str | None
    status: str
    params: dict
    output: str | None
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
