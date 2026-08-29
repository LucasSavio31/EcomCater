"""Registro do módulo `analytics` — tags de marketing (GTM, GA4, Google Ads, Meta)."""
from app.core.module_registry import ModuleSpec, register
from app.modules.analytics import events as _events  # noqa: F401 - registra subscribers
from app.modules.analytics.router_admin import router as admin_router
from app.modules.analytics.router_public import router as public_router

spec = register(
    ModuleSpec(
        slug="analytics",
        label="Rastreamento e anúncios",
        kind="feature",
        toggleable=False,
        public_router=public_router,
        admin_router=admin_router,
        tags=["analytics"],
    )
)
