"""Trava distribuída simples via Redis (SET NX EX).

Uso típico: uvicorn sobe com `--workers N`, e cada worker inicia os mesmos
agendadores (backup, amostragem de saúde). A trava garante que só um worker
executa o tick — sem ela dá backup duplicado e linhas de health repetidas.

Sem Redis (dev/fakeredis cai fora), `acquire` devolve True: assume-se um
único processo.
"""
from __future__ import annotations

import logging

from app.core.redis import redis_client

logger = logging.getLogger("locks")


async def acquire(key: str, ttl_seconds: int) -> bool:
    """True se ESTE processo pegou a trava `key` agora (expira em `ttl_seconds`)."""
    try:
        got = await redis_client.set(f"ecom:lock:{key}", "1", nx=True, ex=ttl_seconds)
        return bool(got)
    except Exception:  # noqa: BLE001
        logger.debug("lock %s: redis indisponível, assumindo processo único", key, exc_info=True)
        return True


async def release(key: str) -> None:
    try:
        await redis_client.delete(f"ecom:lock:{key}")
    except Exception:  # noqa: BLE001
        pass
