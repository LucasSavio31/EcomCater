"""Registro do módulo `upseller` -- 2ª integração do menu Integrações."""
from __future__ import annotations

from app.core.module_registry import ModuleSpec, register
from app.modules.upseller.config import UpSellerConfig
from app.modules.upseller.router_admin import admin_router

spec = register(
    ModuleSpec(
        slug="upseller",
        label="UP Seller",
        kind="feature",
        toggleable=True,
        default_enabled=True,
        default_config=UpSellerConfig().model_dump(),
        admin_router=admin_router,
        tags=["upseller"],
    )
)
