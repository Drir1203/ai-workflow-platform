"""自定义 Agent 执行：从 DB 读取 prompt + param_schema，运行时按参数渲染提示词。

自定义 Agent 没有 Python 类，靠本模块把 DB 记录适配成 Agent Protocol
（key/name/description/param_schema + async run(ctx, params)）。
runner 与 workflow executor 共用 resolve_agent() 解析，保证自定义 Agent
在单跑、工作流步骤、定时调度里都能执行。
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.custom_agent import CustomAgent

from .base import AgentContext
from .registry import AGENT_REGISTRY

_PARAM_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def validate_params(schema: list[dict], params: dict) -> dict:
    """按 param_schema 校验并规整参数：必填缺失/类型不符抛 ValueError。

    - number 类型：已是 int/float 的保留原样（避免 42 → 42.0），字符串再转 float；
    - schema 内可选的空参数（None/""）直接丢弃，避免被 str() 渲染成字面 "None" 污染 prompt；
    - 不在 schema 里的额外参数保留透传（宽松：附加信息也能进 prompt）。
    """
    cleaned: dict[str, Any] = {}
    schema_names: set[str] = set()
    for field in schema or []:
        name = field.get("name")
        if not name:
            continue
        schema_names.add(name)
        raw = params.get(name)
        if raw is None or raw == "":
            if field.get("required"):
                raise ValueError(f"缺少必填参数: {field.get('label') or name}")
            continue
        ftype = field.get("type")
        if ftype == "number":
            if isinstance(raw, bool):
                # bool 是 int 子类，先拦下避免 True 被当数字
                raise ValueError(f"参数 {name} 需要数字")
            if isinstance(raw, (int, float)):
                cleaned[name] = raw
            else:
                try:
                    cleaned[name] = float(raw)
                except (TypeError, ValueError):
                    raise ValueError(f"参数 {name} 需要数字")
        else:
            cleaned[name] = raw
    for k, v in params.items():
        # 只透传 schema 之外的真实参数值；schema 内的可选空参数不补回
        if k not in cleaned and k not in schema_names and v is not None:
            cleaned[k] = v
    return cleaned


def render_prompt(prompt: str, params: dict) -> str:
    """把 prompt 里 {{param}} 占位符替换为参数值；未知占位符替换为空串。"""
    return _PARAM_RE.sub(lambda m: str(params.get(m.group(1), "")), prompt)


class CustomAgentExecutor:
    """把 DB 里的 CustomAgent 记录适配成 Agent Protocol 对象。"""

    def __init__(self, agent: CustomAgent) -> None:
        self.agent = agent
        self.key = agent.key
        self.name = agent.name
        self.description = agent.description or ""
        self.param_schema = agent.param_schema

    async def run(self, ctx: AgentContext, params: dict) -> str:
        # 定时调度/工作流路径可能绕过提交端点，这里兜底校验必填参数
        cleaned = validate_params(self.agent.param_schema, params)
        prompt = render_prompt(self.agent.prompt, cleaned)
        return await ctx.chat(prompt)


async def resolve_agent(db: AsyncSession, agent_key: str) -> Any | None:
    """先查内置注册表，再按 key 查 DB 自定义 Agent；都没有返回 None。"""
    builtin = AGENT_REGISTRY.get(agent_key)
    if builtin is not None:
        return builtin
    result = await db.execute(select(CustomAgent).where(CustomAgent.key == agent_key))
    agent = result.scalar_one_or_none()
    return CustomAgentExecutor(agent) if agent is not None else None
