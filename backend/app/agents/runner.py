import asyncio
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai import get_ai_engine
from app.db import SessionLocal
from app.models import AgentRun, User
from app.services.notification import create_notification

from .base import AgentContext
from .custom import resolve_agent
from .registry import ensure_registered


class RunManager:
    """后台运行任务管理器：POST 提交后立即返回，AI 调用在后台执行并落库。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self.session_factory = session_factory or SessionLocal
        self._tasks: set[asyncio.Task] = set()

    def submit(self, run_id: str) -> None:
        task = asyncio.create_task(self._execute(run_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _execute(self, run_id: str) -> None:
        async with self.session_factory() as db:
            run = await db.get(AgentRun, run_id)
            if run is None:
                return
            run.status = "running"
            run.started_at = datetime.now(timezone.utc)
            await db.commit()
            try:
                user = await db.get(User, run.user_id)
                if user is None:
                    raise ValueError(f"user {run.user_id} not found")
                ensure_registered()
                # 内置 + DB 自定义 Agent 统一解析（自定义 Agent 单跑也能执行）
                agent = await resolve_agent(db, run.agent_key)
                if agent is None:
                    raise ValueError(f"unknown agent: {run.agent_key}")
                ctx = AgentContext(
                    db=db, user=user, engine=get_ai_engine(), tenant_id=run.tenant_id
                )
                run.output = await agent.run(ctx, run.params or {})
                run.status = "succeeded"
            except Exception as exc:  # noqa: BLE001 - 失败写 error 字段，后台任务不崩溃
                run.status = "failed"
                run.error = str(exc)
            finally:
                run.finished_at = datetime.now(timezone.utc)
                # 运行结果通知：best-effort，失败不影响 run 状态落库（create_notification 不 commit）
                if run.status == "succeeded":
                    await create_notification(
                        db,
                        user_id=run.user_id,
                        type="agent_run",
                        title="Agent 运行完成",
                        body=f"Agent「{run.agent_key}」已运行完成",
                        ref_id=run.id,
                        tenant_id=run.tenant_id,
                    )
                else:
                    await create_notification(
                        db,
                        user_id=run.user_id,
                        type="agent_run",
                        title="Agent 运行失败",
                        body=f"Agent「{run.agent_key}」运行失败：{(run.error or '')[:200]}",
                        ref_id=run.id,
                        tenant_id=run.tenant_id,
                    )
                await db.commit()

    async def shutdown(self) -> None:
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()


agent_run_manager = RunManager()
