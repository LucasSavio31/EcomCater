"""Registro do módulo `shipping` (toggleable; provider real = Melhor Envio)."""
from app.core.module_registry import ModuleSpec, register
from app.modules.shipping.config import ShippingConfig
from app.modules.shipping.router_admin import router as admin_router
from app.modules.shipping.router_public import router as public_router
from app.modules.shipping.webhooks import router as webhook_router

spec = register(
    ModuleSpec(
        slug="shipping",
        label="Frete",
        kind="feature",
        toggleable=True,
        default_enabled=True,
        default_config=ShippingConfig().model_dump(),
        public_router=public_router,
        admin_router=admin_router,
        webhook_router=webhook_router,
        tags=["shipping"],
    )
)
