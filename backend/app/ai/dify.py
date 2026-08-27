import json
from collections.abc import AsyncIterator

import httpx

from ..config import settings
from .errors import AiEngineUnavailable


class DifyEngine:
    """复用 Dify CE Service API 作为 AI 引擎（headless，不借其前端）。"""

    def __init__(self, api_url: str | None = None, api_key: str | None = None):
        self.api_url = (api_url or settings.dify_api_url).rstrip("/")
        self.api_key = api_key or settings.dify_api_key

    async def _post(self, path: str, body: dict) -> dict:
        if not self.api_key:
            raise AiEngineUnavailable("AI 引擎未配置（DIFY_API_KEY 为空）")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{self.api_url}{path}", json=body, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def chat(self, query: str, user: str = "unknown") -> str:
        data = await self._post(
            "/chat-messages",
            {
                "inputs": {},
                "query": query,
                "response_mode": "blocking",
                "user": user,
            },
        )
        return data.get("answer", "")

    async def knowledge_query(self, query: str, user: str = "unknown") -> str:
        # MVP：知识库问答复用 chat-messages（在 Dify 侧的应用里挂知识库）；
        # 后续再按项目接 datasets 的 create-by-file 上传文档。
        return await self.chat(query, user)

    async def stream_chat(self, messages: list[dict], user: str = "unknown") -> AsyncIterator[str]:
        """流式对话：``response_mode=streaming`` 逐段产出 answer 增量（打字机效果）。

        MVP 只取最后一条 user 消息单轮生成（Dify 多轮需服务端维护 conversation_id，
        列为后做）。``message_end`` 提前结束；``error`` 事件转 AiEngineUnavailable。
        """
        if not self.api_key:
            raise AiEngineUnavailable("AI 引擎未配置（DIFY_API_KEY 为空）")
        # 多轮场景下取最后一条 user 内容作为本轮 query
        query = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user" and m.get("content")),
            "",
        )
        if not query:
            return
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "inputs": {},
            "query": query,
            "response_mode": "streaming",
            "user": user,
        }
        timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{self.api_url}/chat-messages",
                json=body,
                headers=headers,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if not payload:
                        continue
                    try:
                        data = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    event = data.get("event")
                    if event == "message" and data.get("answer"):
                        yield data["answer"]
                    elif event == "error":
                        raise AiEngineUnavailable(data.get("message") or "Dify 流式错误")
                    elif event == "message_end":
                        return
