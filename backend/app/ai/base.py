from typing import Protocol


class AiEngine(Protocol):
    """AI 引擎抽象接口。业务层只面向本接口，底层可平替 Dify / AnythingLLM / RAGFlow。"""

    async def chat(self, query: str, user: str = "unknown") -> str:
        """对话助手：返回回答文本。"""
        ...

    async def knowledge_query(self, query: str, user: str = "unknown") -> str:
        """知识库 RAG 问答：返回回答文本。"""
        ...
