"""Registro do módulo `products`.

As rotas reais entram na Fase 2. Por ora cada router expõe só `/_ping` para
sanidade. Os agents de execução substituem por `router_public.py` /
`router_admin.py` dedicados (mantendo `service.py` como fonte única da verdade).
"""
from fastapi import APIRouter

from app.core.module_registry import ModuleSpec, register

public_router = APIRouter()
admin_router = APIRouter()


@public_router.get("/_ping")
async def _ping() -> dict:
    return {"module": "products", "scope": "public", "ok": True}


@admin_router.get("/_ping")
async def _ping_admin() -> dict:
    return {"module": "products", "scope": "admin", "ok": True}


spec = register(
    ModuleSpec(
        slug="products",
        label="Produtos",
        kind="domain",
        toggleable=False,
        public_router=public_router,
        admin_router=admin_router,
        tags=["products"],
    )
)
