from app.ai import get_ai_engine
from app.ai.dify import DifyEngine
from app.main import app


class _FakeEngine:
    async def chat(self, query: str, user: str = "unknown") -> str:
        return f"echo:{query}"

    async def knowledge_query(self, query: str, user: str = "unknown") -> str:
        return f"kb:{query}"


async def test_chat_requires_auth(client):
    r = await client.post("/api/ai/chat", json={"query": "hi"})
    assert r.status_code == 401


async def test_chat_returns_answer(client, auth_headers):
    app.dependency_overrides[get_ai_engine] = lambda: _FakeEngine()
    try:
        r = await client.post(
            "/api/ai/chat", json={"query": "今天有什么要跟进？"}, headers=auth_headers
        )
        assert r.status_code == 200
        assert r.json()["answer"] == "echo:今天有什么要跟进？"
    finally:
        app.dependency_overrides.pop(get_ai_engine, None)


async def test_knowledge_returns_answer(client, auth_headers):
    app.dependency_overrides[get_ai_engine] = lambda: _FakeEngine()
    try:
        r = await client.post(
            "/api/ai/knowledge", json={"query": "部署流程是什么"}, headers=auth_headers
        )
        assert r.status_code == 200
        assert r.json()["answer"] == "kb:部署流程是什么"
    finally:
        app.dependency_overrides.pop(get_ai_engine, None)


async def test_chat_empty_query_rejected(client, auth_headers):
    r = await client.post("/api/ai/chat", json={"query": ""}, headers=auth_headers)
    assert r.status_code == 422


async def test_chat_without_dify_config_returns_503(client, auth_headers):
    app.dependency_overrides[get_ai_engine] = lambda: DifyEngine(api_key="")
    try:
        r = await client.post("/api/ai/chat", json={"query": "hi"}, headers=auth_headers)
        assert r.status_code == 503
        assert "未配置" in r.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_ai_engine, None)
