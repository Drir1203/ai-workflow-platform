"""内置 AI 智能体：导入即注册到 AGENT_REGISTRY。"""

from . import competitor_research, inspection_report, interview_questions, weekly_report  # noqa: F401
from .base import Agent, AgentContext, AgentParam, AgentToolError
from .registry import AGENT_REGISTRY, ensure_registered

# 注册 4 个内置 Agent 实例（import 即注册）
AGENT_REGISTRY.register(weekly_report.WeeklyReportAgent())
AGENT_REGISTRY.register(inspection_report.InspectionReportAgent())
AGENT_REGISTRY.register(interview_questions.InterviewQuestionsAgent())
AGENT_REGISTRY.register(competitor_research.CompetitorResearchAgent())

__all__ = [
    "AGENT_REGISTRY",
    "Agent",
    "AgentContext",
    "AgentParam",
    "AgentToolError",
    "ensure_registered",
]
