"""Registro do módulo `financial` (menu Faturamento — livro-caixa cumulativo)."""
from app.core.module_registry import ModuleSpec, register
from app.modules.financial import events as _events  # noqa: F401 - registra subscribers
from app.modules.financial.router_admin import router as admin_router

spec = register(
    ModuleSpec(
        slug="financial",
        label="Faturamento",
        kind="feature",
        toggleable=False,
        admin_router=admin_router,
        tags=["financial"],
    )
)
