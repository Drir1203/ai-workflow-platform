from typing import Literal

from pydantic import BaseModel, Field


class WritingRequest(BaseModel):
    """AI 写作请求：确定动作 + 待处理文本（选中文本或全文）。"""

    operation: Literal["continue", "polish", "summarize"]
    text: str = Field(min_length=1, max_length=200000)  # 上限放宽，让服务端 text_too_long 路径可达
