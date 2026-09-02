"""Rotas públicas do módulo `categories`."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import NS_CATALOG, cached_json
from app.core.database import get_db
from app.modules.categories import service

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/tree")
async def get_tree(db: DbDep) -> list[dict]:
    return await cached_json(
        NS_CATALOG, ("categories:tree",), 300,
        lambda: service.build_tree(db, only_active=True),
    )


async def _by_ref(db: AsyncSession, ref: str) -> dict:
    cat = await service.get_by_slug_or_path(db, ref)
    return service.to_out(cat)


@router.get("/by-path/{path:path}")
async def get_by_path(path: str, db: DbDep) -> dict:
    return await cached_json(
        NS_CATALOG, ("categories:by-path", path), 300, lambda: _by_ref(db, path)
    )


@router.get("/{slug}")
async def get_by_slug(slug: str, db: DbDep) -> dict:
    return await cached_json(
        NS_CATALOG, ("categories:by-slug", slug), 300, lambda: _by_ref(db, slug)
    )
