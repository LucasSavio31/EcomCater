"""Registro do módulo `payment` (toggleable; provider real = Appmax; Fase 5)."""
from fastapi import APIRouter

from app.core.module_registry import ModuleSpec, register

public_router = APIRouter()
admin_router = APIRouter()
webhook_router = APIRouter()


@public_router.get("/_ping")
async def _ping() -> dict:
    return {"module": "payment", "scope": "public", "ok": True}


@admin_router.get("/_ping")
async def _ping_admin() -> dict:
    return {"module": "payment", "scope": "admin", "ok": True}


spec = register(
    ModuleSpec(
        slug="payment",
        label="Pagamento",
        kind="feature",
        toggleable=True,
        default_enabled=True,
        default_config={
            "active_provider": "appmax",
            "providers": {"appmax": {"enabled": True}},
            "methods": {"credit_card": True, "pix": True, "boleto": True},
        },
        public_router=public_router,
        admin_router=admin_router,
        webhook_router=webhook_router,
        tags=["payment"],
    )
)
