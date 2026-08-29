"""Entrada CLI do seed: `python -m app.seed.run`."""
from __future__ import annotations

import asyncio
import logging

from app.bootstrap import discover_modules
from app.core.database import SessionLocal
from app.seed.initial import run_all

logging.basicConfig(level=logging.INFO)


async def _main() -> None:
    discover_modules()  # registra specs de módulo antes de semear a tabela `modules`
    async with SessionLocal() as db:
        await run_all(db)


if __name__ == "__main__":
    asyncio.run(_main())
