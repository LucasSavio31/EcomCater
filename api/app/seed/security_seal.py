"""Selo de "Loja Segura" padrão do rodapé — escudo SSL / site protegido.

    python -m app.seed.security_seal

Idempotente: só cria se a coluna "Loja Segura" ainda não tem imagem.
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

logger = logging.getLogger("seed.security_seal")

SSL_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 76" '
    'font-family="Arial, Helvetica, sans-serif">'
    # escudo verde
    '<path fill="#1E9E3E" d="M32 6c12 4 20 6 20 6v22c0 17-20 30-20 30S12 51 12 34V12s8-2 20-6z"/>'
    # check branco
    '<path fill="none" stroke="#fff" stroke-width="6" stroke-linecap="round" '
    'stroke-linejoin="round" d="M21 34l8 8 15-19"/>'
    # textos
    '<text x="70" y="22" font-size="10" fill="#9aa0a6" letter-spacing="1.5">COMPRA SEGURA</text>'
    '<text x="70" y="44" font-size="19" font-weight="800" fill="#111111">SITE PROTEGIDO</text>'
    '<text x="70" y="60" font-size="10" fill="#9aa0a6" letter-spacing="1.5">CERTIFICADO SSL</text>'
    "</svg>"
)


async def run(db: AsyncSession, *, force: bool = False) -> None:
    row = await get_theme(db)
    seals = _clean_seals(row.footer_seals_json)
    imgs = seals["security"]["images"]
    ours = len(imgs) == 1 and str(imgs[0]).endswith("site-protegido.svg")
    if imgs and not (force and ours):
        logger.info("selo de segurança já configurado — nada a fazer")
        return
    key = f"theme/seals/{uuid.uuid4().hex}/site-protegido.svg"
    storage.save(key, SSL_SVG.encode("utf-8"), "image/svg+xml")
    seals["security"]["images"] = [key]
    if not (seals["security"].get("title") or "").strip():
        seals["security"]["title"] = "Loja Segura"
    row.footer_seals_json = seals
    row.footer_seals_enabled = True
    await db.commit()
    logger.info("selo de segurança padrão instalado: %s", key)


async def _main() -> None:
    logging.basicConfig(level=logging.INFO)
    async with SessionLocal() as db:
        await run(db, force=True)


if __name__ == "__main__":
    asyncio.run(_main())
