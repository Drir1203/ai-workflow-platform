from __future__ import annotations

from datetime import datetime, time, timedelta

from app.models import Note, Project, Task

from .base import Agent, AgentContext, AgentParam, AgentToolError


def _period_start(period: str) -> datetime:
    """计算统计区间起点（周一 00:00 / 上月起点）。"""
    today = datetime.now().date()
    if period == "this_month":
        return datetime.combine(today.replace(day=1), time.min)
    if period == "last_week":
        monday = today - timedelta(days=today.weekday())
        return datetime.combine(monday - timedelta(weeks=1), time.min)
    # this_week
    monday = today - timedelta(days=today.weekday())
    return datetime.combine(monday, time.min)


def _period_label(period: str) -> str:
    return {
        "this_week": "本周",
        "last_week": "上周",
        "this_month": "本月",
    }.get(period, "本周")


def _render_projects(projects: list[Project]) -> str:
    if not projects:
        return "（无项目）"
    return "\n".join(
        f"- {p.name} [{p.status}]：{p.description or '无描述'}" for p in projects
    )


def _render_tasks(tasks: list[Task]) -> str:
    if not tasks:
        return "（该周期内无任务）"
    lines = []
    for t in tasks:
        due = t.due_date.isoformat() if t.due_date else "无截止"
        lines.append(
            f"- [{t.status}][{t.priority}] {t.title}（截止 {due}）：{t.description or ''}"
        )
    return "\n".join(lines)


def _render_notes(notes: list[Note]) -> str:
    if not notes:
        return "（无笔记）"
    return "\n".join(f"- {n.title}：{(n.content or '')[:120]}" for n in notes)


class WeeklyReportAgent:
    key = "weekly_report"
    name = "周报生成"
    description = "根据项目、任务与笔记自动生成本周/上周/本月周报"
    param_schema = [
        AgentParam("project_id", "项目", type="project_id", required=False, default=""),
        AgentParam(
            "period",
            "周期",
            type="select",
            required=False,
            default="this_week",
            options=[
                {"value": "this_week", "label": "本周"},
                {"value": "last_week", "label": "上周"},
                {"value": "this_month", "label": "本月"},
            ],
        ),
    ]

    async def run(self, ctx: AgentContext, params: dict) -> str:
        period = params.get("period") or "this_week"
        project_id = (params.get("project_id") or "").strip() or None

        since = _period_start(period)
        projects = await ctx.get_projects()
        if project_id and not any(p.id == project_id for p in projects):
            raise AgentToolError("项目不存在")

        tasks = await ctx.get_tasks(project_id=project_id, since=since)
        notes = await ctx.get_notes(project_id=project_id)

        scope = "全部项目" if project_id is None else next(
            p.name for p in projects if p.id == project_id
        )
        query = f"""你是一名项目管理助理。请根据以下数据生成{_period_label(period)}周报。

要求：
- 按「本周进展 / 已完成事项 / 问题与风险 / 下周计划」四段组织，输出 Markdown。
- 只依据给定数据陈述；没有数据支撑的内容要明确标注「无数据」，不要编造。
- 涉及任务状态时说明状态含义（todo=待办 / in_progress=进行中 / done=已完成）。

【统计范围】{scope}，周期：{_period_label(period)}

【项目】
{_render_projects(projects)}

【{_period_label(period)}任务】
{_render_tasks(tasks)}

【相关笔记】
{_render_notes(notes)}

请输出周报正文。"""
        return await ctx.chat(query)
