"""Registro central de módulos.

Cada módulo define `spec: ModuleSpec` em seu `module.py`. O `main.py` importa
todos e chama `register_all(app)`, que monta os routers nos prefixos padrão:

    público  -> /api/<slug>/...
    admin    -> /api/admin/<slug>/...
    webhook  -> /api/webhooks/<slug>/...

A habilitação real (liga/desliga + config) vive na tabela `modules` e é lida em
runtime pela dependência `require_module_enabled`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI

ModuleKind = Literal["domain", "feature"]


@dataclass(slots=True)
class ModuleSpec:
    slug: str
    label: str
    kind: ModuleKind = "domain"
    toggleable: bool = False
    default_enabled: bool = True
    default_config: dict = field(default_factory=dict)
    public_router: APIRouter | None = None
    admin_router: APIRouter | None = None
    webhook_router: APIRouter | None = None
    tags: list[str] = field(default_factory=list)


_REGISTRY: dict[str, ModuleSpec] = {}


def register(spec: ModuleSpec) -> ModuleSpec:
    if spec.slug in _REGISTRY:
        raise RuntimeError(f"módulo duplicado: {spec.slug}")
    _REGISTRY[spec.slug] = spec
    return spec


def all_specs() -> list[ModuleSpec]:
    return list(_REGISTRY.values())


def get_spec(slug: str) -> ModuleSpec | None:
    return _REGISTRY.get(slug)


def register_all(app: FastAPI) -> None:
    from app.core.deps import require_module_enabled

    for spec in _REGISTRY.values():
        gate = [Depends(require_module_enabled(spec.slug))] if spec.toggleable else []
        tags = spec.tags or [spec.slug]
        if spec.public_router is not None:
            app.include_router(
                spec.public_router,
                prefix=f"/api/{spec.slug}",
                tags=tags,
                dependencies=gate,
            )
        if spec.admin_router is not None:
            # o próprio módulo `admin` fica na raiz /api/admin (sem repetir o slug)
            admin_prefix = "/api/admin" if spec.slug == "admin" else f"/api/admin/{spec.slug}"
            app.include_router(
                spec.admin_router,
                prefix=admin_prefix,
                tags=[f"admin:{spec.slug}"],
                dependencies=gate,
            )
        if spec.webhook_router is not None:
            app.include_router(
                spec.webhook_router,
                prefix=f"/api/webhooks/{spec.slug}",
                tags=[f"webhook:{spec.slug}"],
            )
