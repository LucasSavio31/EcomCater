"""Agendador interno de backup.

Roda dentro do processo da API (uma task asyncio) e, a cada
`backup_scheduler_interval_seconds`, chama `run_scheduled` — que só cria o
backup se `is_due` (hora local da loja + intervalo da frequência). É idempotente
com o cron externo (`POST /api/system/backup/cron`): o `last_run_at` + a janela
de 20 h impedem execução dupla.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging

from app.core.config import settings
from app.core.database import SessionLocal

logger = logging.getLogger("system.scheduler")

_task: asyncio.Task | None = None


async def _tick_once() -> None:
    from app.core.locks import acquire
    from app.modules.system.digest import maybe_send_daily_digest
    from app.modules.system.service_backup import run_scheduled

    # só um worker por tick (uvicorn --workers N sobe N agendadores)
    if not await acquire("backup-scheduler-tick", ttl_seconds=300):
        return

    async with SessionLocal() as db:
        result = await run_scheduled(db)
    if result.get("ran"):
        logger.info("backup agendado executado: %s", result)

    # resumo diário (idempotente por data — só dispara 1x/dia)
    try:
        async with SessionLocal() as db:
            if await maybe_send_daily_digest(db):
                logger.info("resumo diário enviado")
    except Exception:  # noqa: BLE001
        logger.warning("falha ao enviar o resumo diário", exc_info=True)


async def _loop() -> None:
    interval = max(60, settings.backup_scheduler_interval_seconds)
    logger.info("agendador de backup ativo (intervalo=%ss, fuso=%s)", interval, settings.store_timezone)
    # pequeno atraso no boot para não competir com a subida
    await asyncio.sleep(15)
    while True:
        try:
            await _tick_once()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - nunca deixa a task morrer
            logger.exception("falha no tick do agendador de backup")
        await asyncio.sleep(interval)


def start() -> None:
    global _task
    if not settings.backup_scheduler_enabled or settings.api_env == "test":
        return
    if _task and not _task.done():
        return
    _task = asyncio.create_task(_loop(), name="backup-scheduler")


async def stop() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _task
    _task = None
