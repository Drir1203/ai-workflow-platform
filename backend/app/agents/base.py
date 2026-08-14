from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AiEngine
from app.models import Note, Project, Task, User


@dataclass(frozen=True)
class AgentParam:
    """Agent 参数声明：前端据此渲染表单。

    type: text|textarea|number|select|project_id
    options: [{"value": str, "label": str}, …]（type=select 时使用）
    """

    name: str
    label: str
    type: str = "text"
    required: bool = False
    default: Any = None
    options: list[dict[str, str]] = field(default_factory=list)
    placeholder: str = ""


class AgentToolError(Exception):
    """Agent 工具错误（如引用的项目不存在、必填参数缺失）。"""


class AgentContext:
    """Agent 运行上下文：会话 + 当前用户 + AI 引擎 + 租户。

    提供按 tenant_id 过滤的数据检索工具，供各 Agent 收集上下文。
    """

    def __init__(
        self,
        db: AsyncSession,
        user: User,
        engine: AiEngine,
        tenant_id: str = "default",
    ) -> None:
        self.db = db
        self.user = user
        self.engine = engine
        self.tenant_id = tenant_id

    async def get_projects(self) -> list[Project]:
        result = await self.db.execute(
            select(Project).where(Project.tenant_id == self.tenant_id)
        )
        return list(result.scalars().all())

    async def get_project(self, project_id: str) -> Project | None:
        result = await self.db.execute(
            select(Project).where(
                Project.tenant_id == self.tenant_id, Project.id == project_id
            )
        )
        return result.scalar_one_or_none()

    async def get_tasks(
        self,
        project_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[Task]:
        stmt = select(Task).where(Task.tenant_id == self.tenant_id)
        if project_id:
            stmt = stmt.where(Task.project_id == project_id)
        if since:
            stmt = stmt.where(Task.created_at >= since)
        if until:
            stmt = stmt.where(Task.created_at < until)
        stmt = stmt.order_by(Task.created_at)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_notes(self, project_id: str | None = None) -> list[Note]:
        stmt = select(Note).where(Note.tenant_id == self.tenant_id)
        if project_id:
            stmt = stmt.where(Note.project_id == project_id)
        stmt = stmt.order_by(Note.created_at)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def chat(self, query: str) -> str:
        """调用底层 AI 引擎生成（统一走 chat 接口）。"""
        return await self.engine.chat(query, user=self.user.id)


class Agent(Protocol):
    """Agent 协议：所有内置 Agent 实现此接口。"""

    key: str
    name: str
    description: str
    param_schema: list[AgentParam]

    async def run(self, ctx: AgentContext, params: dict) -> str: ...
