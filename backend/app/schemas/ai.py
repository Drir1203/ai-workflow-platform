from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    project_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
