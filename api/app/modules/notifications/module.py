"""Registro do módulo `notifications` -- sininho do admin."""
from __future__ import annotations

from app.core.module_registry import ModuleSpec, register
from app.modules.notifications import events as _events  # noqa: F401 - registra subscribers
from app.modules.notifications.router_admin import admin_router

spec = register(
    ModuleSpec(
        slug="notifications",
        label="Notificações",
        kind="feature",
        toggleable=False,
        default_enabled=True,
        admin_router=admin_router,
        tags=["notifications"],
    )
)
