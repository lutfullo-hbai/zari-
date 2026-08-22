"""
Xabar almashinuz modellari va javob marshrutizatori.

Queue item'lari va correlation ID asosidagi javob yo'naltirish.
Web so'rovlari request_id bilan keladi — javob to'g'ridan-to'g'ri
shu so'rovni kutayotgan waiter'ga yetkaziladi (race condition himoyasi).
Ovoz va scheduler xabarlari request_id'siz — response_queue (TTS) ga ketadi.
"""

import asyncio
import logging
from dataclasses import dataclass

log = logging.getLogger("zari")


@dataclass
class Incoming:
    """text_queue ga tushadigan xabar."""

    text: str
    source: str = "voice"  # "voice" | "web" | "scheduler"
    request_id: str | None = None


class ResponseRouter:
    """
    request_id -> Future xaritasi.

    Web so'rovi o'z request_id si bilan ro'yxatdan o'tadi,
    llm_worker javob tayyor bo'lganda shu id orqali yechadi.
    """

    def __init__(self) -> None:
        self._waiters: dict[str, asyncio.Future[str]] = {}

    def register(self, request_id: str) -> asyncio.Future[str]:
        future: asyncio.Future[str] = asyncio.get_running_loop().create_future()
        self._waiters[request_id] = future
        return future

    def unregister(self, request_id: str) -> None:
        future = self._waiters.pop(request_id, None)
        if future is not None and not future.done():
            future.cancel()

    def resolve(self, request_id: str | None, response: str) -> bool:
        """Javobni kutayotgan bo'lsa yetkazadi. True — waiter bor edi."""
        if not request_id:
            return False
        future = self._waiters.get(request_id)
        if future is None or future.done():
            return False
        future.set_result(response)
        return True

    def pending_count(self) -> int:
        return len(self._waiters)
