import asyncio
import logging
import ollama
from core.config import settings

log = logging.getLogger("zari")


class OllamaClient:
    def __init__(self, client: ollama.Client | None = None):
        self.client = client or ollama.Client(host=settings.ollama_url)
        self.model = settings.ollama_model
        self.timeout = 300  # 5 minutes default timeout

    def chat(self, messages: list[dict], timeout: int | None = None) -> str:
        """
        Synchronous chat method.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            timeout: Optional timeout in seconds
        
        Returns:
            Response text from the model
        
        Raises:
            Exception: If LLM request fails
        """
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                stream=False
            )
            return response["message"]["content"]
        except Exception as e:
            log.error("LLM chat error: %s", e, exc_info=True)
            raise

    async def chat_async(
        self,
        messages: list[dict],
        timeout: int | None = None
    ) -> str:
        """
        Asynchronous chat method - runs blocking chat in thread pool.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            timeout: Optional timeout in seconds (default: 300)
        
        Returns:
            Response text from the model
        
        Raises:
            asyncio.TimeoutError: If request exceeds timeout
            Exception: If LLM request fails
        """
        request_timeout = timeout or self.timeout
        loop = asyncio.get_event_loop()
        
        try:
            # Run blocking call in executor with timeout
            response = await asyncio.wait_for(
                loop.run_in_executor(None, self.chat, messages),
                timeout=request_timeout
            )
            return response
        except asyncio.TimeoutError:
            log.error("LLM chat timeout after %d seconds", request_timeout)
            raise asyncio.TimeoutError(
                f"LLM response timeout after {request_timeout} seconds"
            )
        except Exception as e:
            log.error("LLM async chat error: %s", e, exc_info=True)
            raise

    async def chat_stream(self, messages: list[dict], timeout: int | None = None):
        """
        Streaming chat method.
        
        Args:
            messages: List of message dicts
            timeout: Optional timeout in seconds
        
        Yields:
            Response chunks as strings
        """
        try:
            stream = self.client.chat(
                model=self.model,
                messages=messages,
                stream=True
            )
            for chunk in stream:
                yield chunk["message"]["content"]
        except Exception as e:
            log.error("LLM stream error: %s", e, exc_info=True)
            raise

    async def chat_stream_async(
        self,
        messages: list[dict],
        timeout: int | None = None
    ):
        """
        Asynchronous streaming chat method.
        
        Args:
            messages: List of message dicts
            timeout: Optional timeout in seconds
        
        Yields:
            Response chunks as strings
        """
        loop = asyncio.get_event_loop()
        request_timeout = timeout or self.timeout
        
        try:
            stream = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.client.chat(
                        model=self.model,
                        messages=messages,
                        stream=True
                    )
                ),
                timeout=request_timeout
            )
            for chunk in stream:
                yield chunk["message"]["content"]
        except asyncio.TimeoutError:
            log.error("LLM stream timeout after %d seconds", request_timeout)
            raise
        except Exception as e:
            log.error("LLM async stream error: %s", e, exc_info=True)
            raise
