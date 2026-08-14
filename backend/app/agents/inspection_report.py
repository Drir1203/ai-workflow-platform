from __future__ import annotations

from datetime import date

from app.models import Task

from .base import Agent, AgentContext, AgentParam, AgentToolError


def _summarize_tasks(tasks: list[Task]) -> str:
    if not tasks:
        return "（该项目暂无任务）"
    lines = []
    for t in tasks:
        due = t.due_date.isoformat() if t.due_date else "无截止"
        lines.append(
            f"- [{t.status}][{t.priority}] {t.title}（截止 {due}）：{t.description or ''}"
        )
    return "\n".join(lines)


class InspectionReportAgent:
    key = "inspection_report"
    name = "巡检报告"
    description = "统计项目任务完成率、高优/逾期任务，生成巡检报告与改进建议"
    param_schema = [AgentParam("project_id", "项目", type="project_id", required=True)]

    async def run(self, ctx: AgentContext, params: dict) -> str:
        project_id = (params.get("project_id") or "").strip()
        if not project_id:
            raise AgentToolError("请选择项目")
        project = await ctx.get_project(project_id)
        if not project:
            raise AgentToolError("项目不存在")

        tasks = await ctx.get_tasks(project_id=project_id)
        total = len(tasks)
        done = sum(1 for t in tasks if t.status == "done")
        in_progress = sum(1 for t in tasks if t.status == "in_progress")
        todo = sum(1 for t in tasks if t.status == "todo")
        high_prio_open = sum(
            1 for t in tasks if t.priority == "high" and t.status != "done"
        )
        overdue = sum(
            1
            for t in tasks
            if t.due_date is not None and t.due_date < date.today() and t.status != "done"
        )
        done_rate = round(done / total * 100, 1) if total else 0

        query = f"""你是一名项目巡检员。请对以下项目生成巡检报告，输出 Markdown。

要求：
- 包含「概览 / 完成率 / 高优与逾期任务 / 风险点 / 改进建议」五部分。
- 只依据给定数据陈述，不编造；无数据项明确标注「无数据」。

【项目】
名称：{project.name}
描述：{project.description or '无描述'}
状态：{project.status}

【任务列表】
{_summarize_tasks(tasks)}

【统计】
- 总任务数：{total}
- 已完成：{done}（完成率 {done_rate}%）
- 进行中：{in_progress}
- 待办：{todo}
- 高优先级未完成：{high_prio_open}
- 逾期未完成：{overdue}

请输出巡检报告正文。"""
        return await ctx.chat(query)
