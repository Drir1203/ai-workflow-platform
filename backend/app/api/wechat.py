from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_db
from ..models.project import Project
from ..models.task import Task
from ..models.user import User
from ..models.wechat_subscription import WechatSubscription
from ..schemas.wechat import (
    WechatReminderResult,
    WechatSubscribeRequest,
    WechatSubscribeResponse,
)
from ..wechat import code2session, send_subscribe_message
from ..wechat.errors import WechatConfigError
from .deps import get_current_user

router = APIRouter(prefix="/api/wechat", tags=["wechat"])


@router.post("/subscribe", response_model=WechatSubscribeResponse)
async def subscribe(
    payload: WechatSubscribeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WechatSubscribeResponse:
    """小程序端 requestSubscribeMessage + wx.login 后，把 openid 绑定到某任务。"""
    task = await db.get(Task, payload.task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    try:
        openid = await code2session(payload.code)
    except WechatConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    template_id = payload.template_id or settings.wechat_template_due
    if not template_id:
        raise HTTPException(
            status_code=400, detail="缺少订阅消息模板 ID（请在 .env 配置 WECHAT_TEMPLATE_DUE）"
        )

    result = await db.execute(
        select(WechatSubscription).where(
            WechatSubscription.user_id == user.id,
            WechatSubscription.task_id == task.id,
        )
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        sub = WechatSubscription(
            user_id=user.id,
            task_id=task.id,
            openid=openid,
            template_id=template_id,
            status="subscribed",
        )
        db.add(sub)
    else:
        sub.openid = openid
        sub.template_id = template_id
        sub.status = "subscribed"
    await db.commit()
    await db.refresh(sub)
    return WechatSubscribeResponse(task_id=task.id, status=sub.status)


@router.post("/reminders/send", response_model=WechatReminderResult)
async def send_reminders(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WechatReminderResult:
    """发送当前用户「今日到期/已逾期且已订阅」任务的到期提醒；v1 客户端触发，
    部署阶段升级为服务端定时推送。"""
    today = date.today()
    stmt = (
        select(WechatSubscription, Task, Project)
        .join(Task, WechatSubscription.task_id == Task.id)
        .join(Project, Task.project_id == Project.id)
        .where(
            WechatSubscription.user_id == user.id,
            WechatSubscription.status == "subscribed",
            Task.due_date <= today,
            Task.status != "done",
        )
    )
    rows = (await db.execute(stmt)).all()

    sent = 0
    skipped = 0
    for sub, task, project in rows:
        try:
            await send_subscribe_message(
                openid=sub.openid,
                template_id=sub.template_id,
                page=f"pages/project/index?project_id={task.project_id}",
                data=_reminder_data(task, project),
            )
            sub.status = "sent"
            sent += 1
        except WechatConfigError:
            skipped += 1
    await db.commit()
    return WechatReminderResult(sent=sent, skipped=skipped)


def _reminder_data(task: Task, project: Project) -> dict[str, dict[str, str]]:
    """订阅消息模板数据（模板字段：thing1=任务、time2=截止、thing3=项目）。"""
    return {
        "thing1": {"value": _truncate(task.title, 20)},
        "time2": {"value": f"{task.due_date or date.today():%Y-%m-%d %H:%M}"},
        "thing3": {"value": _truncate(project.name, 20)},
    }


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"
