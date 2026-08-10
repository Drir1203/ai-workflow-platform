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
