"""
LLM client factory — settings.llm_provider asosida provayderni tanlaydi.

"ollama" -> OllamaClient (local, asosiy)
"groq"   -> GroqClient (cloud fallback, tez)
"""

import logging
from typing import Protocol

from core.config import settings
from llm.groq_client import GroqClient
from llm.ollama import OllamaClient

log = logging.getLogger("zari")

VALID_PROVIDERS = ("ollama", "groq")
DEFAULT_PROVIDER = "ollama"


class LLMClient(Protocol):
    """GroqClient va OllamaClient uchun umumiy interfeys."""

    model: str
    timeout: int

    def chat(self, messages: list[dict], timeout: int | None = None) -> str: ...

    async def chat_async(
        self, messages: list[dict], timeout: int | None = None
    ) -> str: ...

    def chat_stream(self, messages: list[dict], timeout: int | None = None): ...

    async def chat_stream_async(
        self, messages: list[dict], timeout: int | None = None
    ): ...


def create_llm_client(provider: str | None = None) -> LLMClient:
    """settings.llm_provider yoki berilgan provider asosida LLM client qaytaradi."""
    selected = (provider or settings.llm_provider).strip().lower()
    if selected not in VALID_PROVIDERS:
        log.warning(
            "Noma'lum llm_provider '%s', '%s' ishlatiladi", selected, DEFAULT_PROVIDER
        )
        selected = DEFAULT_PROVIDER

    if selected == "groq":
        return GroqClient()
    return OllamaClient()
