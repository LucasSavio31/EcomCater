"""Registro do módulo `theme` (tema visual + páginas institucionais)."""
from app.core.module_registry import ModuleSpec, register
from app.modules.theme.router_admin import router as admin_router
from app.modules.theme.router_public import router as public_router

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
