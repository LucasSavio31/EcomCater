"""Registro do módulo `categories` (rotas reais na Fase 2)."""
from fastapi import APIRouter

from app.core.module_registry import ModuleSpec, register

public_router = APIRouter()
admin_router = APIRouter()


@public_router.get("/_ping")
async def _ping() -> dict:
    return {"module": "categories", "scope": "public", "ok": True}


@admin_router.get("/_ping")
async def _ping_admin() -> dict:
    return {"module": "categories", "scope": "admin", "ok": True}


spec = register(
    ModuleSpec(
        slug="categories",
        label="Categorias",
        kind="domain",
        toggleable=False,
        public_router=public_router,
        admin_router=admin_router,
        tags=["categories"],
    )
)
