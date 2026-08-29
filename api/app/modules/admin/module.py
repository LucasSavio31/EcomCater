"""Registro do módulo `admin` — auth administrativa + dashboard + settings gerais.

Só possui rotas administrativas (sem público).
"""
from app.core.module_registry import ModuleSpec, register
from app.modules.admin.router_admin import router as admin_router

spec = register(
    ModuleSpec(
        slug="admin",
        label="Administração",
        kind="domain",
        toggleable=False,
        admin_router=admin_router,
        tags=["admin"],
    )
)
