import asyncio
import inspect
import logging
from functools import partial

from llm.factory import LLMClient, create_llm_client

log = logging.getLogger("zari")


class Translator:
    def __init__(self, client: LLMClient | None = None):
        self._llm = client or create_llm_client()
        self.timeout = 60

    def uz_to_en(self, text: str) -> str:
        prompt = (
            "You are a translator. Translate the following Uzbek text to English. "
            "Respond with ONLY the English translation, no explanations, no quotes.\n\n"
            f"Uzbek: {text}\n\nEnglish:"
        )
        try:
            translation = self._llm.chat([{"role": "user", "content": prompt}]).strip().strip('"').strip("'")
            log.debug("UZ->EN: '%s' -> '%s'", text, translation)
            return translation
        except Exception as e:
            log.error("Tarjima xatosi (UZ->EN): %s", e)
            return text

    def en_to_uz(self, text: str) -> str:
        prompt = (
            "You are a translator. Translate the following English text to Uzbek. "
            "Respond with ONLY the Uzbek translation, no explanations, no quotes.\n\n"
            f"English: {text}\n\nUzbek:"
        )
        try:
            translation = self._llm.chat([{"role": "user", "content": prompt}]).strip().strip('"').strip("'")
            log.debug("EN->UZ: '%s' -> '%s'", text, translation)
            return translation
        except Exception as e:
            log.error("Tarjima xatosi (EN->UZ): %s", e)
            return text

    async def _run_with_timeout(self, func, *args, timeout: int | None = None):
        request_timeout = timeout or self.timeout
        if inspect.iscoroutinefunction(func):
            return await asyncio.wait_for(func(*args), timeout=request_timeout)

        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, partial(func, *args)),
            timeout=request_timeout,
        )

    async def uz_to_en_async(self, text: str) -> str:
        """Asynchronous Uzbek to English translation"""
        try:
            result = await self._run_with_timeout(self.uz_to_en, text)
            return result if isinstance(result, str) else text
        except TimeoutError:
            log.error("Translation timeout (UZ->EN)")
            return text
        except Exception as e:
            log.error("Async translation error (UZ->EN): %s", e)
            return text

    async def en_to_uz_async(self, text: str) -> str:
        """Asynchronous English to Uzbek translation"""
        try:
            result = await self._run_with_timeout(self.en_to_uz, text)
            return result if isinstance(result, str) else text
        except TimeoutError:
            log.error("Translation timeout (EN->UZ)")
            return text
        except Exception as e:
            log.error("Async translation error (EN->UZ): %s", e)
            return text
