"""Registro do módulo `theme` (tema visual + páginas institucionais)."""
from fastapi import APIRouter

from app.core.module_registry import ModuleSpec, register
from app.modules.theme.router_public import router as public_router

admin_router = APIRouter()


@admin_router.get("/_ping")
async def _ping_admin() -> dict:
    return {"module": "theme", "scope": "admin", "ok": True}


spec = register(
    ModuleSpec(
        slug="theme",
        label="Aparência",
        kind="domain",
        toggleable=False,
        public_router=public_router,
        admin_router=admin_router,
        tags=["theme"],
    )
)
