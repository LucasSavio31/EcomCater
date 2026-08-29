"""Registro do módulo `products` (catálogo)."""
from app.core.module_registry import ModuleSpec, register
from app.modules.products.router_admin import router as admin_router
from app.modules.products.router_public import router as public_router

spec = register(
    ModuleSpec(
        slug="products",
        label="Produtos",
        kind="domain",
        toggleable=False,
        public_router=public_router,
        admin_router=admin_router,
        tags=["products"],
    )
)
