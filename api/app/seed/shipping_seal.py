"""Selo de "Formas de Entrega" padrão do rodapé — logo dos Correios.

    python -m app.seed.shipping_seal

Idempotente: só cria se a coluna "Formas de Entrega" ainda não tem imagem.
Também é chamado pelo seed base (initial.run_all).
"""
from __future__ import annotations

import asyncio
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.modules.theme.service import _clean_seals, get_theme
from app.shared.storage import storage

logger = logging.getLogger("seed.shipping_seal")

# Logo dos Correios simplificado: marca de dupla-seta (amarelo + azul) + wordmark.
CORREIOS_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 210 48" '
    'font-family="Arial, Helvetica, sans-serif">'
    # seta inferior amarela
    '<path fill="#FFC629" d="M2 24 h17 l11 9 -11 9 H2 l11 -9 Z"/>'
    # dobra amarela escura
    '<path fill="#C9971B" d="M19 33 l6 -4 5 4 -6 5 -5 -5 Z"/>'
    # seta superior azul-claro
    '<path fill="#0093D0" d="M12 6 h17 l11 9 -11 9 H12 l11 -9 Z"/>'
    # dobra azul escura
    '<path fill="#002F6C" d="M29 6 h5 l6 5 -5 4 -6 -5 Z"/>'
    # wordmark
    '<text x="52" y="32" font-size="26" font-weight="700" fill="#002F6C" '
    'letter-spacing="-0.5">Correios</text>'
    "</svg>"
)


async def run(db: AsyncSession) -> None:
    row = await get_theme(db)
    seals = _clean_seals(row.footer_seals_json)
    if seals["shipping"]["images"]:
        logger.info("selo de entrega já configurado — nada a fazer")
        return
    key = f"theme/seals/{uuid.uuid4().hex}/correios.svg"
    storage.save(key, CORREIOS_SVG.encode("utf-8"), "image/svg+xml")
    seals["shipping"]["images"] = [key]
    if not (seals["shipping"].get("title") or "").strip():
        seals["shipping"]["title"] = "Formas de Entrega"
    row.footer_seals_json = seals
    row.footer_seals_enabled = True
    await db.commit()
    logger.info("selo de entrega padrão instalado: %s", key)


async def _main() -> None:
    logging.basicConfig(level=logging.INFO)
    async with SessionLocal() as db:
        await run(db)


if __name__ == "__main__":
    asyncio.run(_main())
