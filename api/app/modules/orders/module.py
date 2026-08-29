"""Registro do módulo `orders` (rotas reais nas Fases 5-7)."""
from fastapi import APIRouter

from app.core.module_registry import ModuleSpec, register

public_router = APIRouter()
admin_router = APIRouter()


@public_router.get("/_ping")
async def _ping() -> dict:
    return {"module": "orders", "scope": "public", "ok": True}


@admin_router.get("/_ping")
async def _ping_admin() -> dict:
    return {"module": "orders", "scope": "admin", "ok": True}


spec = register(
    ModuleSpec(
        slug="orders",
        label="Pedidos",
        kind="domain",
        toggleable=False,
        public_router=public_router,
        admin_router=admin_router,
        tags=["orders"],
    )
)
