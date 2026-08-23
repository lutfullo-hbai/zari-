import hashlib
import json
import logging

from core.config import settings

log = logging.getLogger("zari")

_redis = None
_memory_cache: dict[str, str] = {}
_redis_available = True


async def get_redis():
    global _redis, _redis_available
    if not _redis_available:
        return None
    if _redis is None:
        try:
            import redis.asyncio as aioredis

            _redis = aioredis.Redis.from_url(settings.redis_url, decode_responses=True)
            await _redis.ping()
            log.info("Redis connected")
        except Exception as e:
            log.warning("Redis unavailable, using in-memory cache: %s", e)
            _redis_available = False
    return _redis


async def close_redis():
    global _redis, _redis_available
    if _redis:
        try:
            await _redis.aclose()
        except Exception:
            pass
        _redis = None
    _redis_available = True
    log.info("Cache closed")


async def cache_session_messages(session_id: str, messages: list[dict], ttl: int = 3600):
    r = await get_redis()
    if r:
        try:
            key = f"session:{session_id}:messages"
            await r.set(key, json.dumps(messages), ex=ttl)
            return
        except Exception:
            pass
    _memory_cache[f"session:{session_id}:messages"] = json.dumps(messages)


async def get_cached_session_messages(session_id: str) -> list[dict] | None:
    r = await get_redis()
    if r:
        try:
            key = f"session:{session_id}:messages"
            data = await r.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass
    data = _memory_cache.get(f"session:{session_id}:messages")
    if data:
        return json.loads(data)
    return None


async def cache_llm_response(input_text: str, response: str, ttl: int = 86400):
    r = await get_redis()
    if r:
        try:
            key = f"llm:cache:{_hash(input_text)}"
            await r.set(key, response, ex=ttl)
            return
        except Exception:
            pass
    _memory_cache[f"llm:cache:{_hash(input_text)}"] = response


async def get_cached_llm_response(input_text: str) -> str | None:
    r = await get_redis()
    if r:
        try:
            key = f"llm:cache:{_hash(input_text)}"
            return await r.get(key)
        except Exception:
            pass
    return _memory_cache.get(f"llm:cache:{_hash(input_text)}")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()
