"""Registro do módulo `categories`."""
from app.core.module_registry import ModuleSpec, register
from app.modules.categories.router_admin import router as admin_router
from app.modules.categories.router_public import router as public_router

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
