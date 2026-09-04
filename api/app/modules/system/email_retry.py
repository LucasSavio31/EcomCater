"""Agendador de reenvio de e-mail transacional.

Quando o SMTP está fora do ar, `mailer.send` marca a mensagem como `queued`
(com o RFC822 cru). Este loop tenta reenviar a cada
`email_retry_interval_seconds`, com trava de worker único no Redis.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging

from app.core.config import settings
from app.core.database import SessionLocal

logger = logging.getLogger("email_retry.scheduler")

_task: asyncio.Task | None = None


async def _tick_once() -> None:
    from app.core.locks import acquire
    from app.shared.mailer import retry_queued

    if not await acquire("email-retry-tick", ttl_seconds=180):
        return
    async with SessionLocal() as db:
        await retry_queued(db)


async def _loop() -> None:
    interval = max(30, settings.email_retry_interval_seconds)
    logger.info("agendador de reenvio de e-mail ativo (intervalo=%ss)", interval)
    await asyncio.sleep(15)
    while True:
        try:
            await _tick_once()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - nunca deixa a task morrer
            logger.exception("falha no tick de reenvio de e-mail")
        await asyncio.sleep(interval)


def start() -> None:
    global _task
    if not settings.email_retry_enabled or settings.api_env == "test":
        return
    if _task and not _task.done():
        return
    _task = asyncio.create_task(_loop(), name="email-retry-scheduler")


async def stop() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _task
    _task = None
