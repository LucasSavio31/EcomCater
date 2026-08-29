"""Registro do módulo `payment` (toggleable; provider real = Appmax)."""
from app.core.module_registry import ModuleSpec, register
from app.modules.payment.config import PaymentConfig
from app.modules.payment.router_admin import router as admin_router
from app.modules.payment.router_public import router as public_router
from app.modules.payment.webhooks import router as webhook_router

spec = register(
    ModuleSpec(
        slug="payment",
        label="Pagamento",
        kind="feature",
        toggleable=True,
        default_enabled=True,
        default_config=PaymentConfig().model_dump(),
        public_router=public_router,
        admin_router=admin_router,
        webhook_router=webhook_router,
        tags=["payment"],
    )
)
