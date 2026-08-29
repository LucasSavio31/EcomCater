"""Registro do módulo `cart`."""
from app.core.module_registry import ModuleSpec, register
from app.modules.cart.router_public import router as public_router

spec = register(
    ModuleSpec(
        slug="cart",
        label="Carrinho",
        kind="domain",
        toggleable=False,
        public_router=public_router,
        tags=["cart"],
    )
)
