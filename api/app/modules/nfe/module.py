"""Registro do módulo `nfe` (toggleable; emissão de NF-e direto na SEFAZ)."""
from app.core.module_registry import ModuleSpec, register
from app.modules.nfe.config import NfeConfig
from app.modules.nfe.router_admin import admin_router

spec = register(
    ModuleSpec(
        slug="nfe",
        label="NF-e",
        kind="feature",
        toggleable=True,
        default_enabled=True,
        default_config=NfeConfig().model_dump(),
        admin_router=admin_router,
        tags=["nfe"],
    )
)
