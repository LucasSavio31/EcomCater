"""Rate limiting simples por janela fixa, backed por Redis."""
from __future__ import annotations

from fastapi import Request

from app.core.config import settings
from app.core.errors import DomainError
from app.core.redis import redis_client


class RateLimited(DomainError):
    status_code = 429
    code = "rate_limited"


def _parse(rule: str) -> tuple[int, int]:
    """'120/minute' -> (120, 60)."""
    count, _, unit = rule.partition("/")
    seconds = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}[unit.strip().rstrip("s")]
    return int(count), seconds


async def enforce(key: str, rule: str) -> None:
    if settings.api_env == "test":
        return  # a suíte de testes exercita os endpoints em rajada
    limit, window = _parse(rule)
    redis_key = f"rl:{key}:{window}"
    current = await redis_client.incr(redis_key)
    if current == 1:
        await redis_client.expire(redis_key, window)
    if current > limit:
        raise RateLimited("Muitas requisições. Tente de novo em instantes.")


def rate_limit(rule: str, *, scope: str = "ip"):
    """Dependência FastAPI: `Depends(rate_limit('10/minute'))`."""

    async def _dep(request: Request) -> None:
        ident = request.client.host if request.client else "anon"
        await enforce(f"{scope}:{ident}:{request.url.path}", rule)

    return _dep
