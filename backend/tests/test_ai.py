import httpx
import pytest

from app.ai import get_ai_engine
from app.ai.dify import DifyEngine
from app.ai.errors import AiEngineUnavailable
from app.ai.openai_compatible import OpenAICompatibleEngine
from app.config import settings
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


class _FakeAsyncClient:
    """替代 httpx.AsyncClient：记录请求并返回固定 /chat/completions 响应。"""

    def __init__(self, payload=None):
        self.payload = payload or {
            "choices": [{"message": {"content": "deepseek 回复"}}]
        }
        self.sent_url = None
        self.sent_body = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json=None, headers=None):
        self.sent_url = url
        self.sent_body = json
        req = httpx.Request("POST", url, json=json, headers=headers)
        return httpx.Response(200, json=self.payload, request=req)


async def test_openai_compatible_chat_parses_answer(monkeypatch):
    fake = _FakeAsyncClient()
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: fake)
    engine = OpenAICompatibleEngine(
        base_url="https://api.deepseek.com", api_key="sk-test", model="deepseek-chat"
    )
    ans = await engine.chat("你好", user="u1")
    assert ans == "deepseek 回复"
    assert fake.sent_url == "https://api.deepseek.com/chat/completions"
    assert fake.sent_body["model"] == "deepseek-chat"
    assert fake.sent_body["messages"] == [{"role": "user", "content": "你好"}]


async def test_openai_compatible_missing_key_raises(monkeypatch):
    # 显式置空 settings，避免本地 .env 里的真实 key 通过构造函数回退覆盖 api_key=""
    monkeypatch.setattr(settings, "openai_compatible_api_key", "")
    engine = OpenAICompatibleEngine(base_url="https://x", api_key="", model="m")
    with pytest.raises(AiEngineUnavailable):
        await engine.chat("hi")


async def test_openai_compatible_malformed_payload_returns_empty(monkeypatch):
    fake = _FakeAsyncClient(payload={"unexpected": True})
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: fake)
    engine = OpenAICompatibleEngine(
        base_url="https://api.deepseek.com", api_key="sk-test", model="m"
    )
    assert await engine.knowledge_query("部署流程是什么") == ""


# ── stream_chat（SSE 流式）──────────────

class _FakeSSEStream:
    """模拟 client.stream() 返回的响应：raise_for_status + aiter_lines。"""

    def __init__(self, lines):
        self._lines = lines

    def raise_for_status(self):
        return None

    async def aiter_lines(self):
        for l in self._lines:
            yield l


class _FakeStreamCtx:
    def __init__(self, stream):
        self._stream = stream

    async def __aenter__(self):
        return self._stream

    async def __aexit__(self, *a):
        return False


class _FakeStreamClient:
    """替换 httpx.AsyncClient：只实现 stream()，记录请求并返回假 SSE 行。"""

    def __init__(self, lines):
        self._lines = lines
        self.sent = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def stream(self, method, url, json=None, headers=None):
        self.sent = (method, url, json, headers)
        return _FakeStreamCtx(_FakeSSEStream(self._lines))


async def test_openai_stream_chat_parses_deltas(monkeypatch):
    lines = [
        'data: {"choices":[{"delta":{"content":"你"}}]}',
        'data: {"choices":[{"delta":{"content":"好"}}]}',
        'data: {"choices":[{"delta":{}}]}',
        "data: [DONE]",
    ]
    fake = _FakeStreamClient(lines)
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: fake)
    engine = OpenAICompatibleEngine(
        base_url="https://api.deepseek.com", api_key="sk-test", model="deepseek-chat"
    )
    chunks = [
        c
        async for c in engine.stream_chat([{"role": "user", "content": "hi"}], user="u1")
    ]
    assert chunks == ["你", "好"]
    assert fake.sent[1] == "https://api.deepseek.com/chat/completions"
    assert fake.sent[2]["stream"] is True
    assert fake.sent[2]["messages"] == [{"role": "user", "content": "hi"}]


async def test_openai_stream_chat_missing_key_raises(monkeypatch):
    # 显式置空 settings，避免本地 .env 里的真实 key 通过构造函数回退覆盖
    monkeypatch.setattr(settings, "openai_compatible_api_key", "")
    engine = OpenAICompatibleEngine(base_url="https://x", api_key="", model="m")
    with pytest.raises(AiEngineUnavailable):
        async for _ in engine.stream_chat([{"role": "user", "content": "hi"}]):
            pass


async def test_dify_stream_chat_parses_events(monkeypatch):
    lines = [
        'data: {"event":"message","answer":"A"}',
        'data: {"event":"message","answer":"B"}',
        'data: {"event":"message_end"}',
        'data: {"event":"message","answer":"IGNORED"}',  # message_end 后不再产出
    ]
    fake = _FakeStreamClient(lines)
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: fake)
    engine = DifyEngine(api_url="https://dify.example.com/v1", api_key="sk-test")
    chunks = [
        c async for c in engine.stream_chat([{"role": "user", "content": "hi"}], user="u1")
    ]
    assert chunks == ["A", "B"]
    assert fake.sent[1] == "https://dify.example.com/v1/chat-messages"
    assert fake.sent[2]["response_mode"] == "streaming"
    assert fake.sent[2]["query"] == "hi"


async def test_dify_stream_chat_error_event_raises(monkeypatch):
    lines = ['data: {"event":"error","message":"boom"}']
    fake = _FakeStreamClient(lines)
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: fake)
    engine = DifyEngine(api_url="https://dify.example.com/v1", api_key="sk-test")
    with pytest.raises(AiEngineUnavailable):
        async for _ in engine.stream_chat([{"role": "user", "content": "hi"}], user="u1"):
            pass
