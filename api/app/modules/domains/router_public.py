"""Rota pública do módulo `domains`: quais domínios a loja atende (multi-domínio).

Usada pelo middleware da loja (Next) pra separar páginas/cache por domínio.
Só dados públicos -- hostnames já são visíveis no DNS de qualquer jeito.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.modules.domains import sites

public_router = APIRouter()


@public_router.get("/sites")
async def list_sites() -> dict:
    await sites.refresh()
    return {"primary": sites.primary_host(), "hosts": sites.snapshot()["hosts"]}
