from pydantic import BaseModel, Field


class WechatSubscribeRequest(BaseModel):
    code: str = Field(min_length=1)
    task_id: str
    template_id: str | None = None


class WechatSubscribeResponse(BaseModel):
    task_id: str
    status: str


class WechatReminderResult(BaseModel):
    sent: int
    skipped: int
