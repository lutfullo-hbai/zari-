import logging

from db.cache import cache_session_messages, get_cached_session_messages
from db.memory_repo import create_session, save_message, load_messages

log = logging.getLogger("zari")


class SessionMemory:
    def __init__(self):
        self._messages: list[dict] = []
        self._session_id: str | None = None

    async def init(self):
        self._session_id = await create_session()
        log.info("Session started: %s", self._session_id)

    @property
    def session_id(self) -> str | None:
        return self._session_id

    async def add(self, role: str, content: str):
        self._messages.append({"role": role, "content": content})
        if self._session_id:
            await save_message(self._session_id, role, content)
            await cache_session_messages(self._session_id, self._messages)

    def get(self) -> list[dict]:
        return self._messages

    async def load(self, session_id: str | None = None):
        sid = session_id or self._session_id
        if not sid:
            return
        cached = await get_cached_session_messages(sid)
        if cached:
            self._messages = cached
            log.debug("Loaded %d messages from cache", len(cached))
            return
        rows = await load_messages(sid)
        self._messages = rows
        if rows:
            await cache_session_messages(sid, rows)
        log.debug("Loaded %d messages from DB", len(rows))

    def clear(self):
        self._messages = []

    async def system(self, content: str):
        msg = {"role": "system", "content": content}
        self._messages.insert(0, msg)
        if self._session_id:
            await save_message(self._session_id, "system", content)
            await cache_session_messages(self._session_id, self._messages)
