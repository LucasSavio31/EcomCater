"""Agendador interno do envio de recuperação de carrinho abandonado.

Roda dentro do processo da API. A cada `recovery_scheduler_interval_seconds`
chama `_process_due` (com trava de worker único no Redis). É idempotente com
o cron externo `POST /api/cart-recovery/run?token=...` — o mesmo controle de
`reminders_sent` + `delay_minutes` impede reenvio.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging

from app.core.config import settings
from app.core.database import SessionLocal

logger = logging.getLogger("cart_recovery.scheduler")

_task: asyncio.Task | None = None


async def _tick_once() -> None:
    from app.core.locks import acquire
    from app.modules.cart_recovery.module import _process_due

    if not await acquire("cart-recovery-tick", ttl_seconds=240):
        return
    async with SessionLocal() as db:
        res = await _process_due(db)
    if res.get("sent"):
        logger.info("recuperação de carrinho: %s e-mail(s) enviados", res["sent"])


async def _loop() -> None:
    interval = max(60, settings.recovery_scheduler_interval_seconds)
    logger.info("agendador de recuperação de carrinho ativo (intervalo=%ss)", interval)
    await asyncio.sleep(20)  # folga no boot
    while True:
        try:
            await _tick_once()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - nunca deixa a task morrer
            logger.exception("falha no tick de recuperação de carrinho")
        await asyncio.sleep(interval)


def start() -> None:
    global _task
    if not settings.recovery_scheduler_enabled or settings.api_env == "test":
        return
    if _task and not _task.done():
        return
    _task = asyncio.create_task(_loop(), name="cart-recovery-scheduler")


async def stop() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _task
    _task = None
