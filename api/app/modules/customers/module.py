"""Registro do módulo `customers` (auth de cliente + minha-conta)."""
from fastapi import APIRouter

from app.core.module_registry import ModuleSpec, register
from app.modules.customers import events as _events  # noqa: F401 - registra subscribers
from app.modules.customers.router_public import router as public_router

admin_router = APIRouter()


@admin_router.get("/_ping")
async def _ping_admin() -> dict:
    return {"module": "customers", "scope": "admin", "ok": True}


spec = register(
    ModuleSpec(
        slug="customers",
        label="Clientes",
        kind="domain",
        toggleable=False,
        public_router=public_router,
        admin_router=admin_router,
        tags=["customers"],
    )
)
