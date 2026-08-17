"""Web UI uchun Pydantic modellari."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    source: str = "llm"


class StatusResponse(BaseModel):
    status: str
    provider: str
    session_id: str | None = None
    message_count: int = 0
