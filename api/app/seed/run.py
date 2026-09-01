"""Entrada CLI do seed.

    python -m app.seed.run            # seed base (admin, tema, menus, módulos)
    python -m app.seed.run --catalog  # + catálogo de demonstração (categorias/produtos)
"""
from __future__ import annotations

import asyncio
import logging
import sys

from app.bootstrap import discover_modules
from app.core.database import SessionLocal
from app.seed.initial import run_all

logging.basicConfig(level=logging.INFO)


async def _main() -> None:
    discover_modules()  # registra specs de módulo antes de semear a tabela `modules`
    async with SessionLocal() as db:
        await run_all(db)
        if "--catalog" in sys.argv:
            from app.seed.catalog import run as seed_catalog

            await seed_catalog(db)

    # estrutura de navegação (categorias + páginas + menus estilo catlifestyle)
    if "--no-site-content" not in sys.argv:
        from app.seed.site_content import run as seed_site_content

        async with SessionLocal() as db:
            await seed_site_content(db)

    # avaliações de demonstração (estrelas nos cards + nota na PDP)
    if "--catalog" in sys.argv or "--reviews" in sys.argv:
        from app.seed.reviews import run as seed_reviews

        async with SessionLocal() as db:
            await seed_reviews(db)


if __name__ == "__main__":
    asyncio.run(_main())
