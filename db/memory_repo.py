import logging
import uuid

from db.database import get_pool

log = logging.getLogger("zari")


async def create_session() -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        session_id = str(uuid.uuid4())
        await conn.execute("INSERT INTO sessions (id) VALUES ($1)", session_id)
        return session_id


async def load_messages(session_id: str, limit: int = 100) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT role, content FROM messages WHERE session_id = $1 ORDER BY created_at LIMIT $2",
            session_id, limit,
        )
        return [{"role": r["role"], "content": r["content"]} for r in rows]


async def save_message(session_id: str, role: str, content: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES ($1, $2, $3)",
            session_id, role, content,
        )


async def delete_session(session_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM sessions WHERE id = $1", session_id)
