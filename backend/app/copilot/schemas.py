from pydantic import BaseModel, Field


class CopilotMessage(BaseModel):
    """副驾对话单条消息（wire 格式，role 限 user/assistant）。"""

    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=8000)


class CopilotChatRequest(BaseModel):
    """副驾聊天请求：多轮消息 + 可选当前项目上下文。"""

    messages: list[CopilotMessage] = Field(min_length=1, max_length=50)
    project_id: str | None = None
