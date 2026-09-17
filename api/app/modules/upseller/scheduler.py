"""Sincroniza estoque a partir da UP Seller periodicamente -- única direção
que a API pública deles permite (só leitura de armazém/SKU)."""
from __future__ import annotations

import asyncio
import contextlib
import logging

from app.core.config import settings
from app.core.database import SessionLocal

logger = logging.getLogger("upseller.scheduler")

_INTERVAL_SECONDS = 1800  # 30 min -- pagina por armazém/SKU, não é leve
_task: asyncio.Task | None = None


async def _tick_once() -> None:
    from app.modules.upseller.service import is_connected, load_config, sync_stock

    async with SessionLocal() as db:
        try:
            cfg = await load_config(db)
            if not cfg.stock_sync_enabled or not is_connected(cfg):
                return
            result = await sync_stock(db)
            logger.info(
                "UP Seller: %s SKU(s) lido(s), %s variante(s) atualizada(s)",
                result["skus_found"], result["variants_updated"],
            )
        except Exception:
            await db.rollback()
            raise


async def _loop() -> None:
    logger.info("rotina de estoque da UP Seller ativa (intervalo=%ss)", _INTERVAL_SECONDS)
    await asyncio.sleep(60)  # atraso no boot para não competir com a subida
    while True:
        try:
            await _tick_once()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - nunca deixa a task morrer
            logger.exception("falha no tick da rotina da UP Seller")
        await asyncio.sleep(_INTERVAL_SECONDS)


def start() -> None:
    global _task
    if settings.api_env == "test":
        return
    if _task and not _task.done():
        return
    _task = asyncio.create_task(_loop(), name="upseller-stock-sync")


async def stop() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _task
    _task = None
