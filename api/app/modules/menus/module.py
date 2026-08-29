"""Registro do módulo `menus` (menu superior + rodapé; Fase 3/7)."""
from fastapi import APIRouter

from app.core.module_registry import ModuleSpec, register

public_router = APIRouter()
admin_router = APIRouter()


@public_router.get("/_ping")
async def _ping() -> dict:
    return {"module": "menus", "scope": "public", "ok": True}


@admin_router.get("/_ping")
async def _ping_admin() -> dict:
    return {"module": "menus", "scope": "admin", "ok": True}


spec = register(
    ModuleSpec(
        slug="menus",
        label="Menus",
        kind="domain",
        toggleable=False,
        public_router=public_router,
        admin_router=admin_router,
        tags=["menus"],
    )
)
