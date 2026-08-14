from __future__ import annotations

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.db import SessionLocal
from app.models import Workflow, WorkflowRun

from .executor import workflow_run_manager


def _job_id(workflow_id: str) -> str:
    return f"wf-{workflow_id}"


def _build_trigger(schedule: dict):
    """schedule → APScheduler trigger；无效返回 None。"""
    cron = schedule.get("cron")
    if cron:
        return CronTrigger.from_crontab(cron, timezone=settings.scheduler_timezone)
    minutes = schedule.get("interval_minutes")
    if minutes:
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            return None
        if minutes > 0:
            return IntervalTrigger(minutes=minutes)
    return None


class SchedulerService:
    """进程内 APScheduler 单例：按 workflow.schedule 注册/更新 job。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self.session_factory = session_factory or SessionLocal
        self._scheduler: AsyncIOScheduler | None = None

    def _get_scheduler(self) -> AsyncIOScheduler:
        if self._scheduler is None:
            self._scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
        return self._scheduler

    def start(self) -> None:
        sched = self._get_scheduler()
        if not sched.running:
            sched.start()

    async def load_all(self) -> None:
        """启动时加载全部 enabled 且有 schedule 的 workflow。"""
        async with self.session_factory() as db:
            result = await db.execute(select(Workflow).where(Workflow.enabled.is_(True)))
            for wf in result.scalars().all():
                if wf.schedule:
                    self.reschedule(wf)

    def reschedule(self, workflow: Workflow) -> None:
        """按 workflow 的 schedule 注册/更新 job；disabled 或无 schedule 则移除。"""
        if self._scheduler is None:
            return
        self.remove(workflow.id)
        if not workflow.enabled or not workflow.schedule:
            return
        trigger = _build_trigger(workflow.schedule)
        if trigger is None:
            return
        self._scheduler.add_job(
            self._trigger,
            trigger=trigger,
            id=_job_id(workflow.id),
            args=[workflow.id],
            replace_existing=True,
        )

    def remove(self, workflow_id: str) -> None:
        if self._scheduler is None:
            return
        try:
            self._scheduler.remove_job(_job_id(workflow_id))
        except JobLookupError:
            pass

    async def _trigger(self, workflow_id: str) -> None:
        """定时触发：workflow 存在且 enabled 时新建 WorkflowRun 并提交执行。"""
        async with self.session_factory() as db:
            workflow = await db.get(Workflow, workflow_id)
            if workflow is None or not workflow.enabled:
                return
            run = WorkflowRun(
                tenant_id=workflow.tenant_id,
                workflow_id=workflow.id,
                user_id=workflow.user_id,
                status="pending",
                triggered_by="scheduled",
            )
            db.add(run)
            await db.commit()
            await db.refresh(run)
            workflow_run_manager.submit(run.id)

    def shutdown(self) -> None:
        if self._scheduler is not None and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        self._scheduler = None


workflow_scheduler = SchedulerService()
