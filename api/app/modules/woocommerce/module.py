"""Registro do módulo `woocommerce`.

A REST API "de verdade" (`router_public.py`) NÃO passa pelo registry normal
-- ela precisa ficar em `/wp-json/...` (caminho fixo, convenção do
WordPress; quem bate nela é um app de terceiro que não tem como apontar
pra outro lugar), não em `/api/woocommerce/...`. É montada à parte, direto
em `main.py`. Só o `admin_router` (gerenciar chaves) segue o padrão normal.
"""
from __future__ import annotations

from app.core.module_registry import ModuleSpec, register
from app.modules.woocommerce import events as _events  # noqa: F401 - registra subscribers
from app.modules.woocommerce.router_admin import admin_router

spec = register(
    ModuleSpec(
        slug="woocommerce",
        label="Integrações (WooCommerce API)",
        kind="feature",
        toggleable=False,
        default_enabled=True,
        admin_router=admin_router,
        tags=["woocommerce"],
    )
)
