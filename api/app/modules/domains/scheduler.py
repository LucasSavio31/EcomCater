"""Reprocessa domínios pendentes (DNS ainda propagando / falha temporária).

Mais simples que o scheduler do Melhor Envio: intervalo fixo, sem
configuração pelo admin — provisionar domínio é raro, não precisa de
ajuste fino.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal

logger = logging.getLogger("domains.scheduler")

_INTERVAL_SECONDS = 300
_task: asyncio.Task | None = None


async def _tick_once() -> None:
    from sqlalchemy import or_

    from app.modules.domains.models import (
        STATUS_ACTIVE,
        STATUS_AWAITING_NAMESERVERS,
        STATUS_DNS_PENDING,
        STATUS_FAILED,
        Domain,
    )
    from app.modules.domains.service import provision

    async with SessionLocal() as db:
        try:
            pending = await db.scalars(
                select(Domain).where(
                    or_(
                        Domain.status.in_(
                            [STATUS_AWAITING_NAMESERVERS, STATUS_DNS_PENDING, STATUS_FAILED]
                        ),
                        # site já ativo (proxy ok) mas o SSL falhou numa
                        # tentativa anterior — continua tentando emitir.
                        (Domain.status == STATUS_ACTIVE) & (Domain.ssl_status == "error"),
                    )
                )
            )
            for domain in pending:
                await provision(db, domain)
            await db.commit()
        except Exception:
            await db.rollback()
            raise


async def _loop() -> None:
    logger.info("rotina de domínios pendentes ativa (intervalo=%ss)", _INTERVAL_SECONDS)
    await asyncio.sleep(30)  # atraso no boot para não competir com a subida
    while True:
        try:
            await _tick_once()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - nunca deixa a task morrer
            logger.exception("falha no tick da rotina de domínios")
        await asyncio.sleep(_INTERVAL_SECONDS)


def start() -> None:
    global _task
    if settings.api_env == "test":
        return
    if _task and not _task.done():
        return
    _task = asyncio.create_task(_loop(), name="domains-pending-retry")


async def stop() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _task
    _task = None
