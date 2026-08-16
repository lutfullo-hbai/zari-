import logging
import time

from db import cache as cache_module
from db import memory_repo

log = logging.getLogger("zari")

MAX_MESSAGES = 20
MEMORY_TTL = 1800  # 30 daqiqa


class SessionMemory:
    def __init__(self):
        self._messages: list[dict] = []
        self._session_id: str | None = None
        self._last_cleanup: float = time.time()

    async def init(self):
        self._session_id = await memory_repo.create_session()
        log.info("Session started: %s", self._session_id)

    @property
    def session_id(self) -> str | None:
        return self._session_id

    async def add(self, role: str, content: str):
        self._messages.append({"role": role, "content": content})
        await self._maybe_cleanup()
        if self._session_id:
            await memory_repo.save_message(self._session_id, role, content)
            await cache_module.cache_session_messages(self._session_id, self._messages)

    def get(self, max_messages: int = MAX_MESSAGES) -> list[dict]:
        if len(self._messages) <= max_messages:
            return self._messages
        system = [m for m in self._messages if m["role"] == "system"]
        others = [m for m in self._messages if m["role"] != "system"]
        return system + others[-max_messages + len(system):]

    async def load(self, session_id: str | None = None):
        sid = session_id or self._session_id
        if not sid:
            return
        cached = await cache_module.get_cached_session_messages(sid)
        if cached:
            self._messages = cached
            log.debug("Loaded %d messages from cache", len(cached))
            return
        rows = await memory_repo.load_messages(sid)
        self._messages = rows
        if rows:
            await cache_module.cache_session_messages(sid, rows)
        log.debug("Loaded %d messages from DB", len(rows))

    def clear(self):
        self._messages = []
        log.info("Memory cleared")

    async def system(self, content: str):
        msg = {"role": "system", "content": content}
        self._messages.insert(0, msg)
        if self._session_id:
            await memory_repo.save_message(self._session_id, "system", content)
            await cache_module.cache_session_messages(self._session_id, self._messages)

    async def _maybe_cleanup(self):
        now = time.time()
        if now - self._last_cleanup < MEMORY_TTL:
            return

        self._last_cleanup = now
        old_count = len(self._messages)

        if old_count <= MAX_MESSAGES:
            return

        system_msgs = [m for m in self._messages if m["role"] == "system"]
        other_msgs = [m for m in self._messages if m["role"] != "system"]
        self._messages = system_msgs + other_msgs[-MAX_MESSAGES:]

        new_count = len(self._messages)
        if old_count != new_count:
            log.info("Memory cleanup: %d -> %d messages", old_count, new_count)
            if self._session_id:
                await cache_module.cache_session_messages(self._session_id, self._messages)
