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
    source: str = "builtin"  # builtin（内置 Python 类）| custom（DB 持久化的自定义 Agent）
    prompt: str | None = None  # 仅自定义 Agent 返回，供前端编辑回填（内置 Agent 无提示词）


class CustomAgentCreate(BaseModel):
    """用户自定义 Agent 创建：prompt 支持 {{param}} 占位符。"""

    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    prompt: str = Field(min_length=1, max_length=50000)
    param_schema: list[AgentParamInfo] = Field(default_factory=list, max_length=50)


class CustomAgentUpdate(BaseModel):
    """自定义 Agent 更新：全字段可选，None 表示不修改。"""

    name: str | None = Field(None, max_length=120)
    description: str | None = None
    prompt: str | None = Field(None, max_length=50000)
    param_schema: list[AgentParamInfo] | None = Field(None, max_length=50)


class CustomAgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    key: str
    name: str
    description: str | None
    prompt: str
    param_schema: list[AgentParamInfo]
    created_at: datetime
    updated_at: datetime


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
