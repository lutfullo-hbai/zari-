import logging
import asyncpg

from core.config import settings

log = logging.getLogger("zari")

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=1,
            max_size=5,
        )
    return _pool


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages(session_id, created_at);
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS persona (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                confidence REAL DEFAULT 1.0,
                source TEXT DEFAULT 'manual',
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id SERIAL PRIMARY KEY,
                title TEXT DEFAULT '',
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                tags TEXT DEFAULT ''
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_content ON notes(content)
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS wiki (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    log.info("Database initialized")


async def close_db():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        log.info("Database pool closed")
