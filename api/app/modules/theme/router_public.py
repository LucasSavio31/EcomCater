"""Rotas públicas do módulo `theme` — tema (SSR) e páginas institucionais."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import NS_CONTENT, NS_THEME, cached_json
from app.core.database import get_db
from app.modules.theme import service

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def _theme_payload(db: AsyncSession) -> dict:
    out = service.theme_out(await service.get_theme(db))
    # dados da loja usados no rodapé (copyright / CNPJ)
    from app.modules.admin.models import StoreSettings

    store = await db.get(StoreSettings, 1)
    if store:
        out["store_name"] = store.store_name
        out["legal_name"] = store.legal_name
        out["cnpj"] = store.cnpj
        out["social_json"] = store.social_json or {}
    return out


@router.get("")
async def get_theme(db: DbDep) -> dict:
    return await cached_json(NS_THEME, ("theme:public",), 300, lambda: _theme_payload(db))


@router.get("/pages/{slug}")
async def get_page(slug: str, db: DbDep) -> dict:
    return await cached_json(
        NS_CONTENT, ("theme:page", slug), 300,
        lambda: _page_payload(db, slug),
    )


async def _page_payload(db: AsyncSession, slug: str) -> dict:
    return service.page_out(await service.get_page(db, slug))
