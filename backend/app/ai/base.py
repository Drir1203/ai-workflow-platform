from collections.abc import AsyncIterator
from typing import Protocol


class AiEngine(Protocol):
    """AI 引擎抽象接口。业务层只面向本接口，底层可平替 Dify / AnythingLLM / RAGFlow。"""

    async def chat(self, query: str, user: str = "unknown") -> str:
        """对话助手：返回回答文本。"""
        ...

    async def knowledge_query(self, query: str, user: str = "unknown") -> str:
        """知识库 RAG 问答：返回回答文本。"""
        ...

    async def stream_chat(self, messages: list[dict], user: str = "unknown") -> AsyncIterator[str]:
        """流式对话：按消息列表（多轮）逐段产出回答文本。

        用于 AI 副驾等需要打字机效果的多轮场景；单轮场景仍走 chat()。
        """
        ...
