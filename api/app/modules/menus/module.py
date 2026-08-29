"""Registro do módulo `menus`."""
from app.core.module_registry import ModuleSpec, register
from app.modules.menus.router_admin import router as admin_router
from app.modules.menus.router_public import router as public_router

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
