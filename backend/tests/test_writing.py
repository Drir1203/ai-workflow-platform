import pytest

from app.ai import get_ai_engine
from app.ai.errors import AiEngineUnavailable
from app.main import app
from app.writing import service as writing_service

# 每个 operation 的中文关键词，用于断言 system prompt 随操作切换
_PROMPT_KEYWORDS = {"continue": "续写", "polish": "润色", "summarize": "摘要"}


class _WritingEngine:
    """捕获消息的假引擎：stream_chat 分块产出，记录每次收到的 messages。"""

    def __init__(self, output="流式输出结果", fail_with=None):
        self.output = output
        self.fail_with = fail_with  # AiEngineUnavailable 实例：首次 stream_chat 即抛
        self.received: list[list[dict]] = []
        self.stream_count = 0

    async def stream_chat(self, messages: list[dict], user: str = "unknown"):
        self.stream_count += 1
        self.received.append(messages)
        if self.fail_with is not None:
            raise self.fail_with
        # 模拟真实流式：分两块产出同一段文本
        yield self.output[:2]
        yield self.output[2:]


def _use_engine(engine: _WritingEngine) -> None:
    app.dependency_overrides[get_ai_engine] = lambda: engine


def _drop_engine() -> None:
    app.dependency_overrides.pop(get_ai_engine, None)


async def test_writing_requires_auth(client):
    r = await client.post("/api/writing", json={"operation": "continue", "text": "你好"})
    assert r.status_code == 401


@pytest.mark.parametrize("operation", ["continue", "polish", "summarize"])
async def test_writing_streams_text_and_done(client, auth_headers, operation):
    engine = _WritingEngine()
    _use_engine(engine)
    try:
        r = await client.post(
            "/api/writing",
            json={"operation": operation, "text": "原始文本"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert '"type": "text"' in r.text
        # 假引擎分两块产出，SSE 行间有 \n 分隔，故按块断言
        assert "流式" in r.text
        assert "输出结果" in r.text
        assert '"type": "done"' in r.text
        # 恰好一次流式调用，且 system prompt 随 operation 变化
        assert engine.stream_count == 1
        sys_prompt = engine.received[0][0]
        assert sys_prompt["role"] == "system"
        assert _PROMPT_KEYWORDS[operation] in sys_prompt["content"]
        assert engine.received[0][1]["content"] == "原始文本"
    finally:
        _drop_engine()


async def test_writing_engine_unavailable_error_event(client, auth_headers):
    engine = _WritingEngine(fail_with=AiEngineUnavailable("AI 引擎未配置"))
    _use_engine(engine)
    try:
        r = await client.post(
            "/api/writing",
            json={"operation": "polish", "text": "待润色文本"},
            headers=auth_headers,
        )
        # 全请求 200：引擎未配置走 error 事件而非 503（流已开始）
        assert r.status_code == 200
        assert '"code": "ai_unavailable"' in r.text
        assert '"type": "done"' in r.text
    finally:
        _drop_engine()


async def test_writing_continue_truncates_tail(client, auth_headers, monkeypatch):
    monkeypatch.setattr(writing_service.settings, "writing_max_chars", 10)
    text = "一二三四五六七八九十一二三四五六七八九十"  # 20 字符，超过上限
    engine = _WritingEngine()
    _use_engine(engine)
    try:
        r = await client.post(
            "/api/writing",
            json={"operation": "continue", "text": text},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert '"type": "done"' in r.text
        # 续写只截尾部作上下文：发出去的 user 消息应只剩后 10 字符
        assert engine.received[0][1]["content"] == text[-10:]
    finally:
        _drop_engine()


async def test_writing_polish_too_long_error(client, auth_headers, monkeypatch):
    monkeypatch.setattr(writing_service.settings, "writing_max_chars", 10)
    engine = _WritingEngine()
    _use_engine(engine)
    try:
        r = await client.post(
            "/api/writing",
            json={"operation": "polish", "text": "一二三四五六七八九十太多了"},  # 13 字符
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert '"code": "text_too_long"' in r.text
        assert '"type": "done"' in r.text
        # 改写对截断语义失真，宁可报错也不调 LLM
        assert engine.stream_count == 0
    finally:
        _drop_engine()


async def test_writing_empty_text_error(client, auth_headers):
    engine = _WritingEngine()
    _use_engine(engine)
    try:
        r = await client.post(
            "/api/writing",
            json={"operation": "polish", "text": "   "},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert '"code": "empty_text"' in r.text
        assert '"type": "done"' in r.text
        assert engine.stream_count == 0
    finally:
        _drop_engine()
