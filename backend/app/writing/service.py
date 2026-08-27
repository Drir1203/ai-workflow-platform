"""AI 写作编排：事件构造 + 截断 + 流式产出。

事件协议（router 序列化为 ``data: {json}\n\n``）：
  {"type":"text", "delta": str}
  {"type":"done"}
  {"type":"error", "code": str, "message": str}   # 后跟 done
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.config import settings

from .prompts import build_writing_messages


def event_text(delta: str) -> dict:
    return {"type": "text", "delta": delta}


def event_done() -> dict:
    return {"type": "done"}


def event_error(code: str, message: str) -> dict:
    return {"type": "error", "code": code, "message": message}


async def stream_writing(engine, user, operation: str, text: str) -> AsyncIterator[dict]:
    """主流程：空文本 / 超长校验 → 流式产出改写文本 → done。

    max_chars 在函数内读取 settings，便于测试 monkeypatch。
    """
    if not text.strip():
        yield event_error("empty_text", "文本为空，请先输入内容")
        yield event_done()
        return

    max_chars = settings.writing_max_chars
    if len(text) > max_chars:
        if operation == "continue":
            # 续写只需结尾作上下文，截尾部即可
            text = text[-max_chars:]
        else:
            # 润色/总结对截断内容语义失真，宁可提示用户分段处理
            yield event_error("text_too_long", f"文本过长（超过 {max_chars} 字符），请选中部分文本或分段处理")
            yield event_done()
            return

    messages = build_writing_messages(operation, text)
    async for chunk in engine.stream_chat(messages, user.id):
        yield event_text(chunk)
    yield event_done()
