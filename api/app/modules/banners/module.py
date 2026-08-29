"""Registro do módulo `banners` (toggleable; vitrines da home; Fase 3/7)."""
from fastapi import APIRouter

from app.core.module_registry import ModuleSpec, register

public_router = APIRouter()
admin_router = APIRouter()


@public_router.get("/_ping")
async def _ping() -> dict:
    return {"module": "banners", "scope": "public", "ok": True}


@admin_router.get("/_ping")
async def _ping_admin() -> dict:
    return {"module": "banners", "scope": "admin", "ok": True}


spec = register(
    ModuleSpec(
        slug="banners",
        label="Banners",
        kind="feature",
        toggleable=True,
        default_enabled=True,
        public_router=public_router,
        admin_router=admin_router,
        tags=["banners"],
    )
)
