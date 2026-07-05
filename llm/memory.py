import logging

from db import cache as cache_module
from db import memory_repo

log = logging.getLogger("zari")


class SessionMemory:
    def __init__(self):
        self._messages: list[dict] = []
        self._session_id: str | None = None

    async def init(self):
        self._session_id = await memory_repo.create_session()
        log.info("Session started: %s", self._session_id)

    @property
    def session_id(self) -> str | None:
        return self._session_id

    async def add(self, role: str, content: str):
        self._messages.append({"role": role, "content": content})
        if self._session_id:
            await memory_repo.save_message(self._session_id, role, content)
            await cache_module.cache_session_messages(self._session_id, self._messages)

    def get(self, max_messages: int = 20) -> list[dict]:
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

    async def system(self, content: str):
        msg = {"role": "system", "content": content}
        self._messages.insert(0, msg)
        if self._session_id:
            await memory_repo.save_message(self._session_id, "system", content)
            await cache_module.cache_session_messages(self._session_id, self._messages)
