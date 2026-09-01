"""Registro do módulo `system` — saúde da infra + backup."""
from app.core.module_registry import ModuleSpec, register
from app.modules.system.router_admin import admin_router, public_router

spec = register(
    ModuleSpec(
        slug="system",
        label="Sistema (saúde + backup)",
        kind="domain",
        toggleable=False,
        admin_router=admin_router,
        public_router=public_router,
        tags=["system"],
    )
)
