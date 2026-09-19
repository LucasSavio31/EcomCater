"""Consulta periodicamente a SEFAZ pelos documentos ainda `processing`
(a autorização é assíncrona: o envio só devolve um recibo, o resultado sai
depois). Mesmo molde simples do `domains/scheduler.py` — intervalo fixo, sem
ajuste fino pelo admin."""
from __future__ import annotations

import asyncio
import contextlib
import logging

from app.core.config import settings
from app.core.database import SessionLocal

logger = logging.getLogger("nfe.scheduler")

_INTERVAL_SECONDS = 45
_task: asyncio.Task | None = None


async def _tick_once() -> None:
    from app.modules.nfe import service

    async with SessionLocal() as db:
        try:
            await service.poll_pending(db)
            await db.commit()
        except Exception:
            await db.rollback()
            raise


async def _loop() -> None:
    logger.info("rotina de consulta de NF-e pendente ativa (intervalo=%ss)", _INTERVAL_SECONDS)
    await asyncio.sleep(20)
    while True:
        try:
            await _tick_once()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - nunca deixa a task morrer
            logger.exception("falha no tick da rotina de NF-e")
        await asyncio.sleep(_INTERVAL_SECONDS)


def start() -> None:
    global _task
    if settings.api_env == "test":
        return
    if _task and not _task.done():
        return
    _task = asyncio.create_task(_loop(), name="nfe-poll-pending")


async def stop() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _task
    _task = None
