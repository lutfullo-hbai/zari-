import hashlib
import logging
import json

import redis.asyncio as aioredis

from core.config import settings

log = logging.getLogger("zari")

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def close_redis():
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
        log.info("Redis closed")


async def cache_session_messages(session_id: str, messages: list[dict], ttl: int = 3600):
    r = await get_redis()
    key = f"session:{session_id}:messages"
    await r.set(key, json.dumps(messages), ex=ttl)


async def get_cached_session_messages(session_id: str) -> list[dict] | None:
    r = await get_redis()
    key = f"session:{session_id}:messages"
    data = await r.get(key)
    if data:
        return json.loads(data)
    return None


async def cache_llm_response(input_text: str, response: str, ttl: int = 86400):
    r = await get_redis()
    key = f"llm:cache:{_hash(input_text)}"
    await r.set(key, response, ex=ttl)


async def get_cached_llm_response(input_text: str) -> str | None:
    r = await get_redis()
    key = f"llm:cache:{_hash(input_text)}"
    return await r.get(key)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()
