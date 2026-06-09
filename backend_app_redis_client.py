import asyncio
from typing import Any

from upstash_redis import Redis

from app.core.config import get_settings


class UpstashRedisClient:
    def __init__(self, client: Redis | None = None) -> None:
        settings = get_settings()
        self._client = client or Redis(
            url=settings.upstash_redis_rest_url,
            token=settings.upstash_redis_rest_token,
        )

    async def get(self, key: str) -> Any:
        return await asyncio.to_thread(self._client.get, key)

    async def set(self, key: str, value: Any, expire_seconds: int | None = None) -> bool:
        if expire_seconds is None:
            result = await asyncio.to_thread(self._client.set, key, value)
        else:
            result = await asyncio.to_thread(self._client.set, key, value, ex=expire_seconds)
        return bool(result)

    async def delete(self, key: str) -> int:
        result = await asyncio.to_thread(self._client.delete, key)
        return int(result or 0)

    async def expire(self, key: str, seconds: int) -> bool:
        result = await asyncio.to_thread(self._client.expire, key, seconds)
        return bool(result)


redis_client = UpstashRedisClient()