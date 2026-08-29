"""Rotas públicas do módulo `categories`."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.categories import service

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/tree")
async def get_tree(db: DbDep) -> list[dict]:
    return await service.build_tree(db, only_active=True)


@router.get("/by-path/{path:path}")
async def get_by_path(path: str, db: DbDep) -> dict:
    cat = await service.get_by_slug_or_path(db, path)
    return service.to_out(cat)


@router.get("/{slug}")
async def get_by_slug(slug: str, db: DbDep) -> dict:
    cat = await service.get_by_slug_or_path(db, slug)
    return service.to_out(cat)
