"""Registro do módulo `cart` (rotas reais na Fase 4)."""
from fastapi import APIRouter

from app.core.module_registry import ModuleSpec, register

public_router = APIRouter()


@public_router.get("/_ping")
async def _ping() -> dict:
    return {"module": "cart", "scope": "public", "ok": True}


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
