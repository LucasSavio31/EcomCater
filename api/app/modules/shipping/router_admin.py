"""Rotas administrativas do módulo `shipping`: configuração + teste de cotação."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin, require_role
from app.modules.admin.models import AdminUser
from app.modules.shipping import service
from app.modules.shipping.providers.base import Package
from app.modules.shipping.schemas import ShippingConfigIn

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]
AdminRoleDep = Annotated[AdminUser, Depends(require_role("admin"))]


@router.get("/config")
async def get_config(db: DbDep, _: AdminDep) -> dict:
    cfg = await service.load_config(db)
    return {
        "active_provider": cfg.active_provider,
        "origin_zip": cfg.origin_zip,
        "melhor_envio_sandbox": cfg.melhor_envio_sandbox,
        "has_token": bool(cfg.melhor_envio_token),
        "default_package": cfg.default_package.model_dump(),
        "free_shipping_services": cfg.free_shipping_services,
    }


@router.put("/config")
async def update_config(body: ShippingConfigIn, db: DbDep, _: AdminRoleDep) -> dict:
    cfg = await service.save_config(db, body.model_dump(exclude_unset=True))
    return {"active_provider": cfg.active_provider, "origin_zip": cfg.origin_zip, "has_token": bool(cfg.melhor_envio_token)}


@router.post("/test-quote")
async def test_quote(
    db: DbDep,
    _: AdminDep,
    dest_zip: str = Query(min_length=8, max_length=8),
) -> list[dict]:
    return await service.quote(
        db,
        dest_zip=dest_zip,
        packages=[Package(weight_grams=500, length_mm=200, width_mm=150, height_mm=100, insurance_cents=10000)],
    )
