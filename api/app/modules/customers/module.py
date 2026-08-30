"""Registro do módulo `customers` (auth de cliente + minha-conta + CRUD admin)."""
from app.core.module_registry import ModuleSpec, register
from app.modules.customers import events as _events  # noqa: F401 - registra subscribers
from app.modules.customers.router_admin import router as admin_router
from app.modules.customers.router_public import router as public_router


spec = register(
    ModuleSpec(
        slug="customers",
        label="Clientes",
        kind="domain",
        toggleable=False,
        public_router=public_router,
        admin_router=admin_router,
        tags=["customers"],
    )
)
