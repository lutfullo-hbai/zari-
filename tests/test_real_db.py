"""
Haqiqiy PostgreSQL integratsiya testlari.

Mock emas — docker'dagi zari-db ga (yoki CI service'iga) real ulanadi.
DB topilmasa testlar SKIP bo'ladi (local dev buzilmaydi),
CI'da esa services postgres har doim mavjud.

Majburlash uchun: ZARI_DB_TESTS=1
"""

import asyncio
import os

import pytest

DB_URL = os.getenv("DATABASE_URL", "postgresql://zari:zari@localhost:5434/zari")


def _db_available() -> bool:
    if os.getenv("ZARI_DB_TESTS") != "1":
        return False
    try:
        asyncio.run(_ping())
        return True
    except Exception:
        return False


async def _ping():
    import asyncpg

    conn = await asyncio.wait_for(asyncpg.connect(DB_URL), timeout=3)
    await conn.close()


pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not _db_available(), reason="PostgreSQL mavjud emas"),
]


@pytest.fixture
async def fresh_pool():
    """Har test toza pool bilan boshlaydi, oxirida yopadi."""
    import db.database as dbm

    dbm._pool = None
    yield dbm
    await dbm.close_db()
    dbm._pool = None


class TestRealDatabase:
    async def test_init_db_creates_all_tables(self, fresh_pool):
        from db.database import get_pool, init_db

        await init_db()
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public'")
            names = {r["tablename"] for r in rows}
        expected = {"sessions", "messages", "persona", "notes", "wiki", "scheduled_tasks", "alembic_version"}
        assert expected.issubset(names)

    async def test_init_db_idempotent_twice(self, fresh_pool):
        """init_db ikki marta chaqirilsa ham xato bermasligi kerak."""
        from db.database import init_db

        await init_db()
        await init_db()

    async def test_alembic_version_at_head(self, fresh_pool):
        from db.database import get_pool, init_db

        await init_db()
        pool = await get_pool()
        async with pool.acquire() as conn:
            ver = await conn.fetchval("SELECT version_num FROM alembic_version")
        assert ver == "002_scheduled_tasks"

    async def test_memory_roundtrip_real_db(self, fresh_pool):
        """Session → xabar saqlash → qayta o'qish (memory_repo orqali)."""
        from db.database import init_db
        from db.memory_repo import create_session, load_messages, save_message

        await init_db()
        sid = await create_session()
        await save_message(sid, "user", "salom zari")
        await save_message(sid, "assistant", "salom! nima gap?")

        rows = await load_messages(sid)
        roles = [r["role"] for r in rows]
        contents = [r["content"] for r in rows]
        assert "user" in roles and "assistant" in roles
        assert "salom zari" in contents

    async def test_scheduler_task_lifecycle_real_db(self, fresh_pool):
        """add_task → list → remove (haqiqiy scheduled_tasks jadvalida)."""
        from core.scheduler import add_task, list_tasks, remove_task
        from db.database import init_db

        await init_db()
        task = await add_task(
            name="audit-test",
            message="bu test xabari",
            schedule_type="once",
            schedule_value="2030-01-01T08:00:00",
        )
        try:
            tasks = await list_tasks()
            assert any(t.id == task.id and t.name == "audit-test" for t in tasks)
        finally:
            removed = await remove_task(task.id)
            assert removed is True

        tasks_after = await list_tasks()
        assert all(t.id != task.id for t in tasks_after)

    async def test_persona_roundtrip_real_db(self, fresh_pool):
        """UserPersona set/get/delete real persona jadvalida."""
        from db.database import init_db
        from llm.persona import UserPersona

        await init_db()
        persona = UserPersona()
        await persona.ensure_table()

        await persona.set("audit_key", "qiymat", category="test", source="pytest")
        got = await persona.get("audit_key")
        assert got == "qiymat"

        deleted = await persona.delete("audit_key")
        assert deleted is True
        assert await persona.get("audit_key") is None


class TestRealRedis:
    @pytest.mark.skipif(not _db_available(), reason="Redis tekshiruvi DB flag'iga bog'langan")
    async def test_cache_llm_roundtrip(self, fresh_pool):
        import json

        import redis.asyncio as aioredis

        url = os.getenv("REDIS_URL", "redis://localhost:6380/0")
        client = aioredis.from_url(url, decode_responses=True)
        try:
            await client.set("zari:test:key", json.dumps({"a": 1}), ex=60)
            raw = await client.get("zari:test:key")
            assert json.loads(raw) == {"a": 1}
            await client.delete("zari:test:key")
        finally:
            await client.aclose()
