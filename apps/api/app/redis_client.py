import redis.asyncio as redis

from app.config import get_settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis | None:
    global _client
    if _client is None:
        try:
            _client = redis.from_url(get_settings().redis_url, decode_responses=True)
        except Exception:
            return None
    return _client
