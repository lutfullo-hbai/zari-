from unittest.mock import AsyncMock, patch

import pytest


class TestCache:
    @pytest.mark.asyncio
    async def test_cache_llm_response(self):
        mock_redis = AsyncMock()
        with patch("db.cache.get_redis", return_value=mock_redis):
            from db.cache import cache_llm_response

            await cache_llm_response("salom", "Hello")

            args, kwargs = mock_redis.set.call_args
            key = args[0]
            assert key.startswith("llm:cache:")
            assert args[1] == "Hello"
            assert kwargs["ex"] == 86400

    @pytest.mark.asyncio
    async def test_get_cached_llm_response(self):
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "Hello"
        with patch("db.cache.get_redis", return_value=mock_redis):
            from db.cache import get_cached_llm_response

            result = await get_cached_llm_response("salom")

            assert result == "Hello"

    @pytest.mark.asyncio
    async def test_get_cached_llm_response_miss(self):
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        with patch("db.cache.get_redis", return_value=mock_redis):
            from db.cache import get_cached_llm_response

            result = await get_cached_llm_response("salom")

            assert result is None

    @pytest.mark.asyncio
    async def test_cache_session_messages(self):
        mock_redis = AsyncMock()
        with patch("db.cache.get_redis", return_value=mock_redis):
            from db.cache import cache_session_messages

            msgs = [{"role": "user", "content": "salom"}]
            await cache_session_messages("sess-1", msgs)

            mock_redis.set.assert_called_once()
            args, kwargs = mock_redis.set.call_args
            assert args[0] == "session:sess-1:messages"
            assert "salom" in args[1]
            assert kwargs["ex"] == 3600

    @pytest.mark.asyncio
    async def test_get_cached_session_messages(self):
        mock_redis = AsyncMock()
        import json

        mock_redis.get.return_value = json.dumps([{"role": "user", "content": "salom"}])
        with patch("db.cache.get_redis", return_value=mock_redis):
            from db.cache import get_cached_session_messages

            result = await get_cached_session_messages("sess-1")

            assert result == [{"role": "user", "content": "salom"}]

    @pytest.mark.asyncio
    async def test_get_cached_session_messages_miss(self):
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        with patch("db.cache.get_redis", return_value=mock_redis):
            from db.cache import get_cached_session_messages

            result = await get_cached_session_messages("sess-1")

            assert result is None

    @pytest.mark.asyncio
    async def test_close_redis(self):
        import db.cache

        mock_redis = AsyncMock()
        db.cache._redis = mock_redis

        await db.cache.close_redis()

        mock_redis.aclose.assert_called_once()
        assert db.cache._redis is None

        db.cache._redis = None

    def test_hash_deterministic(self):
        from db.cache import _hash

        assert _hash("salom") == _hash("salom")
        assert _hash("salom") != _hash("hello")


class TestDatabase:
    @pytest.mark.asyncio
    async def test_init_db_delegates_to_alembic(self):
        """init_db endi alembic upgrade head ni chaqiradi (bitta schema manba)."""
        import db.database

        db.database._pool = None

        with patch("alembic.command.upgrade") as mock_upgrade, patch("alembic.config.Config") as mock_config_cls:
            await db.database.init_db()

            mock_upgrade.assert_called_once_with(mock_config_cls.return_value, "head")

        db.database._pool = None

    @pytest.mark.asyncio
    async def test_get_pool_returns_same_instance(self):
        import asyncpg

        import db.database

        db.database._pool = None

        mock_pool = AsyncMock()
        with patch.object(asyncpg, "create_pool", new_callable=AsyncMock, return_value=mock_pool):
            pool1 = await db.database.get_pool()
            pool2 = await db.database.get_pool()

            assert pool1 is pool2

        db.database._pool = None

    @pytest.mark.asyncio
    async def test_close_db_resets_pool(self):
        import db.database

        mock_pool = AsyncMock()
        db.database._pool = mock_pool

        await db.database.close_db()

        assert db.database._pool is None
        mock_pool.close.assert_called_once()

        db.database._pool = None
