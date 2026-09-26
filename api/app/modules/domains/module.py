"""Registro do módulo `domains` — domínio próprio, proxy reverso + SSL automáticos."""
from app.core.module_registry import ModuleSpec, register
from app.modules.domains.router_admin import admin_router
from app.modules.domains.router_public import public_router

spec = register(
    ModuleSpec(
        slug="domains",
        label="Domínio",
        kind="domain",
        toggleable=False,
        admin_router=admin_router,
        public_router=public_router,
        tags=["domains"],
    )
)
