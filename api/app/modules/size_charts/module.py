"""Registro do módulo `size_charts` — tabelas de medidas."""
from app.core.module_registry import ModuleSpec, register
from app.modules.size_charts.router_admin import router as admin_router

spec = register(
    ModuleSpec(
        slug="size_charts",
        label="Tabelas de medidas",
        kind="domain",
        toggleable=False,
        admin_router=admin_router,
        tags=["size_charts"],
    )
)
