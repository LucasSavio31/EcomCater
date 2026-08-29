"""Cliente Redis compartilhado (sessão de carrinho, cache de frete, rate limit).

Em produção/Docker: `redis://...`. Para rodar sem infra de Redis no dev local,
use `REDIS_URL=fakeredis://` — sobe um Redis em memória, no próprio processo.
"""
from __future__ import annotations

import redis.asyncio as aioredis

from app.core.config import settings

if settings.redis_url.startswith(("fakeredis://", "memory://")):
    import fakeredis.aioredis as fakeredis

    redis_client: aioredis.Redis = fakeredis.FakeRedis(decode_responses=True)
else:
    redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


async def get_redis() -> aioredis.Redis:
    return redis_client
