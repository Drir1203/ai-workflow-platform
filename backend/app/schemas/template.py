"""参数预置模板 schema：把一组参数值存成命名模板，运行 Agent/编辑工作流步骤时复用。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _cap_params(v: dict) -> dict:
    """参数模板 params 键数上限，防异常大 payload 刷爆存储。"""
    if len(v) > 100:
        raise ValueError("params 字段数过多")
    return v


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    agent_key: str = Field(min_length=1, max_length=80)  # 绑定哪个智能体
    params: dict = Field(default_factory=dict)

    _cap_params_create = field_validator("params")(_cap_params)


class TemplateUpdate(BaseModel):
    name: str | None = None
    params: dict | None = None

    _cap_params_update = field_validator("params")(_cap_params)


class TemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    agent_key: str
    params: dict
    created_at: datetime
    updated_at: datetime
