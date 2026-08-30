"""Selo de pagamento padrão do rodapé — tira com as bandeiras dos métodos.

    python -m app.seed.payment_seal

Idempotente: só cria se a coluna "Formas de Pagamento" ainda não tem imagem.
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

logger = logging.getLogger("seed.payment_seal")


def _badge(x: int, body: str, *, bg: str = "#ffffff", stroke: str = "#e5e5e5") -> str:
    return (
        f'<g transform="translate({x},0)">'
        f'<rect width="60" height="38" rx="6" fill="{bg}" stroke="{stroke}"/>'
        f"{body}</g>"
    )


# Bandeiras simplificadas no estilo oficial (cores de marca), sobre badge branco.
PAYMENT_BADGES_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 522 38" '
    'font-family="Arial, Helvetica, sans-serif">'
    # Mastercard
    + _badge(
        0,
        '<circle cx="25" cy="19" r="10" fill="#EB001B"/>'
        '<circle cx="37" cy="19" r="10" fill="#F79E1B"/>'
        '<path d="M31 11a10 10 0 0 0 0 16 10 10 0 0 0 0-16z" fill="#FF5F00"/>',
    )
    # Visa
    + _badge(
        66,
        '<text x="30" y="25" font-size="15" font-weight="700" font-style="italic" '
        'fill="#1A1F71" text-anchor="middle" letter-spacing="1">VISA</text>',
    )
    # Elo
    + _badge(
        132,
        '<circle cx="17" cy="10" r="2.4" fill="#FFCB05"/>'
        '<circle cx="30" cy="8" r="2.4" fill="#EF4123"/>'
        '<circle cx="43" cy="10" r="2.4" fill="#00A4E0"/>'
        '<text x="30" y="27" font-size="14" font-weight="700" font-style="italic" '
        'fill="#111111" text-anchor="middle">elo</text>',
        bg="#ffffff",
    )
    # Hipercard
    + _badge(
        198,
        '<text x="30" y="23" font-size="8.5" font-weight="700" fill="#fff" '
        'text-anchor="middle">Hipercard</text>',
        bg="#B3131B",
        stroke="#B3131B",
    )
    # American Express
    + _badge(
        264,
        '<text x="30" y="24" font-size="12" font-weight="800" fill="#fff" '
        'text-anchor="middle" letter-spacing="1">AMEX</text>',
        bg="#006FCF",
        stroke="#006FCF",
    )
    # Diners Club
    + _badge(
        330,
        '<circle cx="30" cy="15" r="8" fill="#0079BE"/>'
        '<rect x="29" y="7" width="2" height="16" fill="#fff"/>'
        '<text x="30" y="32" font-size="6.5" font-weight="700" fill="#0079BE" '
        'text-anchor="middle">DINERS</text>',
    )
    # Boleto
    + _badge(
        396,
        "".join(
            f'<rect x="{12 + i * 3}" y="8" width="{1 + (i % 3)}" height="16" fill="#222"/>'
            for i in range(11)
        )
        + '<text x="30" y="32" font-size="7" font-weight="700" fill="#333" '
        'text-anchor="middle">Boleto</text>',
    )
    # Pix
    + _badge(
        462,
        '<g transform="translate(30 16) rotate(45)">'
        '<rect x="-9" y="-9" width="18" height="18" rx="4" fill="#32BCAD"/>'
        "</g>"
        '<text x="30" y="33" font-size="7.5" font-weight="700" fill="#32BCAD" '
        'text-anchor="middle">pix</text>',
    )
    + "</svg>"
)


async def run(db: AsyncSession) -> None:
    row = await get_theme(db)
    seals = _clean_seals(row.footer_seals_json)
    if seals["payment"]["images"]:
        logger.info("selo de pagamento já configurado — nada a fazer")
        return
    key = f"theme/seals/{uuid.uuid4().hex}/pagamento.svg"
    storage.save(key, PAYMENT_BADGES_SVG.encode("utf-8"), "image/svg+xml")
    seals["payment"]["images"] = [key]
    if not (seals["payment"].get("title") or "").strip():
        seals["payment"]["title"] = "Formas de Pagamento"
    row.footer_seals_json = seals
    row.footer_seals_enabled = True
    await db.commit()
    logger.info("selo de pagamento padrão instalado: %s", key)


async def _main() -> None:
    logging.basicConfig(level=logging.INFO)
    async with SessionLocal() as db:
        await run(db)


if __name__ == "__main__":
    asyncio.run(_main())
