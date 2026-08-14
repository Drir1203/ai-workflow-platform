from __future__ import annotations

from .base import Agent


class AgentRegistry:
    """key → Agent 实例的注册表。"""

    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        self._agents[agent.key] = agent

    def get(self, key: str) -> Agent | None:
        return self._agents.get(key)

    def list(self) -> list[Agent]:
        return list(self._agents.values())


AGENT_REGISTRY = AgentRegistry()


def ensure_registered() -> None:
    """惰性导入 4 个内置 Agent 模块以触发注册（防御直接 import 子模块的场景）。"""
    from . import competitor_research, inspection_report, interview_questions, weekly_report  # noqa: F401
