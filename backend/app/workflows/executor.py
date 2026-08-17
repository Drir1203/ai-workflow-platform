import asyncio
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai import get_ai_engine
from app.db import SessionLocal
from app.models import User, Workflow, WorkflowRun

from ..agents.base import AgentContext
from ..agents.custom import resolve_agent
from ..agents.registry import ensure_registered


def interpolate(value: Any, results: list[dict]) -> Any:
    """递归替换字符串模板。

    {{prev_output}}       → 上一步 output（无上一步则空串）
    {{step.N.output}}     → results[N].output
    dict/list 递归替换。
    """
    if isinstance(value, str):
        prev = results[-1].get("output") if results else None
        out = value.replace("{{prev_output}}", prev or "")
        for i, r in enumerate(results):
            out = out.replace(f"{{{{step.{i}.output}}}}", r.get("output") or "")
        return out
    if isinstance(value, dict):
        return {k: interpolate(v, results) for k, v in value.items()}
    if isinstance(value, list):
        return [interpolate(v, results) for v in value]
    return value


class WorkflowRunManager:
    """工作流执行管理：顺序跑 steps，任一步失败即终止并记录已完成的 results。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self.session_factory = session_factory or SessionLocal
        self._tasks: set[asyncio.Task] = set()

    def submit(self, run_id: str) -> None:
        task = asyncio.create_task(self._execute(run_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _execute(self, run_id: str) -> None:
        async with self.session_factory() as db:
            run = await db.get(WorkflowRun, run_id)
            if run is None:
                return
            run.status = "running"
            run.started_at = datetime.now(timezone.utc)
            await db.commit()
            try:
                workflow = await db.get(Workflow, run.workflow_id)
                if workflow is None:
                    raise ValueError(f"workflow {run.workflow_id} not found")
                user = await db.get(User, run.user_id)
                if user is None:
                    raise ValueError(f"user {run.user_id} not found")
                ensure_registered()

                results: list[dict] = []
                for step in workflow.steps or []:
                    agent_key = step.get("agent_key")
                    # 内置 + DB 自定义 Agent 统一解析（自定义步骤在定时调度里也能执行）
                    agent = await resolve_agent(db, agent_key)
                    if agent is None:
                        raise ValueError(f"unknown agent: {agent_key}")
                    params = interpolate(step.get("params") or {}, results)
                    ctx = AgentContext(
                        db=db,
                        user=user,
                        engine=get_ai_engine(),
                        tenant_id=workflow.tenant_id,
                    )
                    output = await agent.run(ctx, params)
                    results.append(
                        {
                            "label": step.get("label") or agent.name,
                            "agent_key": agent_key,
                            "output": output,
                        }
                    )
                run.results = results
                run.status = "succeeded"
            except Exception as exc:  # noqa: BLE001 - 失败写 error，后台任务不崩溃
                run.status = "failed"
                run.error = str(exc)
            finally:
                run.finished_at = datetime.now(timezone.utc)
                await db.commit()

    async def shutdown(self) -> None:
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()


workflow_run_manager = WorkflowRunManager()
