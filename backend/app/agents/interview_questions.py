from __future__ import annotations

from .base import Agent, AgentContext, AgentParam, AgentToolError

_DIFFICULTY_LABEL = {"easy": "简单", "medium": "中等", "hard": "困难"}


class InterviewQuestionsAgent:
    key = "interview_questions"
    name = "押题生成"
    description = "根据主题生成面试/考试押题，含考察点与参考答案要点"
    param_schema = [
        AgentParam("topic", "主题", required=True, placeholder="如：FastAPI 异步编程"),
        AgentParam("count", "题目数量", type="number", default=10),
        AgentParam(
            "difficulty",
            "难度",
            type="select",
            default="medium",
            options=[
                {"value": "easy", "label": "简单"},
                {"value": "medium", "label": "中等"},
                {"value": "hard", "label": "困难"},
            ],
        ),
    ]

    async def run(self, ctx: AgentContext, params: dict) -> str:
        topic = (params.get("topic") or "").strip()
        if not topic:
            raise AgentToolError("请填写主题")
        raw_count = params.get("count")
        try:
            count = int(raw_count) if raw_count is not None else 10
        except (TypeError, ValueError):
            count = 10
        count = max(1, min(count, 20))
        difficulty = params.get("difficulty") or "medium"
        difficulty_label = _DIFFICULTY_LABEL.get(difficulty, "中等")

        query = f"""你是资深面试官。请围绕主题「{topic}」生成 {count} 道{difficulty_label}难度押题，输出 Markdown。

要求：
- 每题包含：题目 / 考察点 / 参考答案要点（3-5 条）。
- 难度与{difficulty_label}匹配，覆盖面广、避免重复。
- 请输出编号题库（1. 2. 3. …）。"""
        return await ctx.chat(query)
