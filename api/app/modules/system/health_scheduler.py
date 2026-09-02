"""Amostragem periódica da saúde dos serviços.

Roda dentro do processo da API (uma task asyncio) e grava uma amostra por
serviço em cada janela de 15 min (…:00, :15, :30, :45), mesmo que ninguém
esteja com o painel de Infraestrutura aberto. `run_checks` já deduplica por
janela, então rodar mais vezes é inofensivo.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import time

from app.core.config import settings
from app.core.database import SessionLocal

logger = logging.getLogger("system.health_scheduler")

_BUCKET = 15 * 60
_task: asyncio.Task | None = None


async def _tick_once() -> None:
    from app.core.locks import acquire
    from app.modules.system.service_health import run_checks

    # só um worker amostra por janela (uvicorn --workers N sobe N amostradores)
    if not await acquire("health-sample-tick", ttl_seconds=120):
        return

    async with SessionLocal() as db:
        try:
            await run_checks(db, persist=True)  # faz o próprio commit
        except Exception:
            await db.rollback()
            raise


async def _loop() -> None:
    logger.info("amostragem de saúde ativa (1 leitura por janela de 15 min)")
    await asyncio.sleep(10)  # pequena folga no boot
    with contextlib.suppress(Exception):
        await _tick_once()  # amostra imediata ao subir
    while True:
        # dorme até logo depois do início da próxima janela de 15 min
        wait = _BUCKET - (time.time() % _BUCKET) + 5
        try:
            await asyncio.sleep(wait)
        except asyncio.CancelledError:
            raise
        try:
            await _tick_once()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - nunca deixa a task morrer
            logger.exception("falha na amostragem de saúde")


def start() -> None:
    global _task
    if not settings.health_scheduler_enabled or settings.api_env == "test":
        return
    if _task and not _task.done():
        return
    _task = asyncio.create_task(_loop(), name="health-sampler")


async def stop() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _task
    _task = None
