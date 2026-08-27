"""Web UI uchun Pydantic modellari."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class TaskCreateRequest(BaseModel):
    name: str = Field(default="task", min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=4000)
    schedule_type: str = Field(default="once", pattern="^(once|daily|interval)$")
    schedule_value: str = Field(default="", max_length=100)


class ChatResponse(BaseModel):
    response: str
    source: str = "llm"


class StatusResponse(BaseModel):
    status: str
    provider: str
    session_id: str | None = None
    message_count: int = 0
