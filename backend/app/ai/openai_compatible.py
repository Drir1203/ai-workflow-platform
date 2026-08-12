import httpx

from ..config import settings
from .errors import AiEngineUnavailable


class OpenAICompatibleEngine:
    """OpenAI 兼容引擎（DeepSeek / 通义 DashScope / 任何 OpenAI 协议端点）。

    与 DifyEngine 平替：业务层只面向 AiEngine Protocol（chat / knowledge_query）。
    走标准 ``/chat/completions``，无需自建服务即可让 AI 面板真实对话。
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self.base_url = (base_url or settings.openai_compatible_base_url).rstrip("/")
        self.api_key = api_key or settings.openai_compatible_api_key
        self.model = model or settings.openai_compatible_model

    async def _chat_completion(self, query: str, user: str = "unknown") -> str:
        if not self.api_key:
            raise AiEngineUnavailable("AI 引擎未配置（OPENAI_COMPATIBLE_API_KEY 为空）")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": query}],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions", json=body, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return ""

    async def chat(self, query: str, user: str = "unknown") -> str:
        return await self._chat_completion(query, user)

    async def knowledge_query(self, query: str, user: str = "unknown") -> str:
        # MVP：知识库问答复用同一 LLM（后续接 RAG 再拆分）
        return await self._chat_completion(query, user)
