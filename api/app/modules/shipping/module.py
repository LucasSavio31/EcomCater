"""Registro do módulo `shipping` (toggleable; provider real = Melhor Envio; Fase 4)."""
from fastapi import APIRouter

from app.core.module_registry import ModuleSpec, register

public_router = APIRouter()
admin_router = APIRouter()
webhook_router = APIRouter()


@public_router.get("/_ping")
async def _ping() -> dict:
    return {"module": "shipping", "scope": "public", "ok": True}


@admin_router.get("/_ping")
async def _ping_admin() -> dict:
    return {"module": "shipping", "scope": "admin", "ok": True}


spec = register(
    ModuleSpec(
        slug="shipping",
        label="Frete",
        kind="feature",
        toggleable=True,
        default_enabled=True,
        default_config={
            "active_provider": "melhor_envio",
            "origin_zip": "01001000",
            "default_package": {"weight_grams": 300, "length_mm": 200, "width_mm": 150, "height_mm": 100},
        },
        public_router=public_router,
        admin_router=admin_router,
        webhook_router=webhook_router,
        tags=["shipping"],
    )
)
