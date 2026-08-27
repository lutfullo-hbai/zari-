import logging

from core.config import settings

log = logging.getLogger("zari")

_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        import asyncpg

        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=2,
            max_size=10,
        )
        log.info("PostgreSQL pool connected")
    return _pool


async def init_db():
    """
    Schema yaratish — bitta manba: alembic migratsiyalari.

    init_db() endi to'g'ridan-to'g'ri CREATE TABLE yozmaydi,
    `alembic upgrade head` ni ishga tushiradi. Shu bilan alembic
    va runtime schema o'rtasidagi drift oldini olinadi.
    """
    import asyncio
    from pathlib import Path

    from alembic.config import Config

    from alembic import command

    ini_path = Path(__file__).resolve().parent.parent / "alembic.ini"
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)

    # Alembic sinxron API — thread'da ishga tushiramiz
    await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
    log.info("Database migrations applied (alembic upgrade head)")


async def close_db():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        log.info("Database closed")
