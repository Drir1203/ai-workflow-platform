import json
from collections.abc import AsyncIterator

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

    async def stream_chat(self, messages: list[dict], user: str = "unknown") -> AsyncIterator[str]:
        """流式对话：``stream: True`` 走 SSE，逐段产出 content 增量（打字机效果）。

        供 AI 副驾多轮场景使用；单轮仍走 chat()。read timeout=60s 是「两次读取
        间隔」而非总时长，连续输出不会被误杀。
        """
        if not self.api_key:
            raise AiEngineUnavailable("AI 引擎未配置（OPENAI_COMPATIBLE_API_KEY 为空）")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=body,
                headers=headers,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if not payload or payload == "[DONE]":
                        continue
                    try:
                        data = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    choices = data.get("choices") or []
                    if not choices:
                        continue
                    delta = (choices[0].get("delta") or {}).get("content")
                    if delta:
                        yield delta
