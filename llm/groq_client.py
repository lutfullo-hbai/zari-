"""
Groq API client — OllamaClient bilan bir xil interfeys.

Vaqtincha: kompyuter imkoniyati kichkinaligi uchun Groq API ishlatilmoqda.
Loyiha to'liq yakunlangandan keyin local Ollama ga qaytish mumkin.
"""

import asyncio
import logging
from collections.abc import AsyncIterator

from groq import Groq

from core.config import settings

log = logging.getLogger("zari")


class GroqClient:
    """Groq API client — OllamaClient bilan mos interfeys."""

    def __init__(self, client: Groq | None = None):
        self.client = client or Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model
        self.timeout = 120

    def chat(self, messages: list[dict], timeout: int | None = None) -> str:
        """
        Sync chat — Groq API orqali javob oladi.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2048,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            log.error("Groq chat xatosi: %s", e, exc_info=True)
            raise

    async def chat_async(
        self,
        messages: list[dict],
        timeout: int | None = None,
    ) -> str:
        """
        Async chat — blocking call ni thread pool da ishlaydi.
        """
        request_timeout = timeout or self.timeout
        loop = asyncio.get_event_loop()
        try:
            response = await asyncio.wait_for(
                loop.run_in_executor(None, self.chat, messages),
                timeout=request_timeout,
            )
            return response
        except TimeoutError:
            log.error("Groq chat timeout — %d soniyadan oshdi", request_timeout)
            raise TimeoutError(f"Groq response timeout after {request_timeout} seconds")
        except Exception as e:
            log.error("Groq async chat xatosi: %s", e, exc_info=True)
            raise

    async def chat_stream(
        self,
        messages: list[dict],
        timeout: int | None = None,
    ) -> AsyncIterator[str]:
        """
        Sync streaming chat.
        """
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2048,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            log.error("Groq stream xatosi: %s", e, exc_info=True)
            raise

    async def chat_stream_async(
        self,
        messages: list[dict],
        timeout: int | None = None,
    ) -> AsyncIterator[str]:
        """
        Async streaming chat.
        """
        loop = asyncio.get_event_loop()
        request_timeout = timeout or self.timeout
        try:
            stream = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: list(
                        self.client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            temperature=0.7,
                            max_tokens=2048,
                            stream=True,
                        )
                    ),
                ),
                timeout=request_timeout,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except TimeoutError:
            log.error("Groq async stream timeout — %d soniya", request_timeout)
            raise
        except Exception as e:
            log.error("Groq async stream xatosi: %s", e, exc_info=True)
            raise
