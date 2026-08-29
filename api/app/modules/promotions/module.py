"""Registro do módulo `promotions` (toggleable). Rotas públicas de cupom vivem
em `cart` (`POST /api/cart/coupon`); aqui só o CRUD administrativo."""
from app.core.module_registry import ModuleSpec, register
from app.modules.promotions.router_admin import router as admin_router

spec = register(
    ModuleSpec(
        slug="promotions",
        label="Promoções",
        kind="feature",
        toggleable=True,
        default_enabled=True,
        admin_router=admin_router,
        tags=["promotions"],
    )
)
