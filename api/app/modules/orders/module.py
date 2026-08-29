"""Registro do módulo `orders`."""
from app.core.module_registry import ModuleSpec, register
from app.modules.orders import events as _events  # noqa: F401 - registra subscribers
from app.modules.orders.router_admin import router as admin_router
from app.modules.orders.router_public import router as public_router

spec = register(
    ModuleSpec(
        slug="orders",
        label="Pedidos",
        kind="domain",
        toggleable=False,
        public_router=public_router,
        admin_router=admin_router,
        tags=["orders"],
    )
)
