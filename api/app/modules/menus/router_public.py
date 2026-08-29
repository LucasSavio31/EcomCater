"""Rotas públicas do módulo `menus`."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.menus import service

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/{location}")
async def get_menu(location: str, db: DbDep) -> list[dict]:
    if location not in ("header", "footer"):
        return []
    return await service.get_location(db, location, only_active=True)
