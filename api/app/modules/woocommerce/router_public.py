"""A REST API do WooCommerce de verdade, pra qualquer app que já sabe
conversar com uma loja WooCommerce (o app "WooCommerce" do Bling, por
exemplo) enxergar esta loja igual enxergaria uma loja WordPress real.

Montado à parte em `main.py`, em `/wp-json` -- FORA do prefixo `/api/...`
dos demais módulos, porque o caminho é fixo por convenção do WordPress e
apps de terceiro não têm como apontar pra outro lugar.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import NotFoundError
from app.modules.woocommerce import service
from app.modules.woocommerce.auth import WcAuthDep

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("")
@router.get("/")
async def wp_json_root() -> dict:
    """Descoberta -- alguns clientes batem aqui antes de tudo pra confirmar
    que o site tem a REST API do WordPress/WooCommerce."""
    return {
        "name": "WooCommerce",
        # "wc/v2" também é servido (idêntico ao v3) -- confirmado em produção
        # que a Frenet valida a integração batendo primeiro em
        # /wp-json/wc/v2/system_status, não v3.
        "namespaces": ["wc/v3", "wc/v2"],
    }


@router.get("/wc/v3")
@router.get("/wc/v2")
async def wc_namespace_index() -> dict:
    return {"namespace": "wc/v3"}


@router.get("/wc/v3/system_status")
@router.get("/wc/v2/system_status")
async def system_status(_: WcAuthDep) -> dict:
    return {
        "environment": {"platform": "custom", "version": "1.0"},
        "settings": {"currency": "BRL"},
    }


@router.get("/wc/v3/customers")
@router.get("/wc/v2/customers")
async def list_customers(_: WcAuthDep) -> list[dict]:
    # Pedidos aqui trazem o endereço/CPF direto no próprio recurso (guest
    # checkout) -- não temos um cadastro de "cliente WooCommerce" à parte.
    return []


# ---------------------------------------------------------------- pedidos

def _paged(request_query: dict, items: list[dict], total: int, per_page: int) -> JSONResponse:
    import math

    return JSONResponse(
        content=items,
        headers={
            "X-WP-Total": str(total),
            "X-WP-TotalPages": str(max(1, math.ceil(total / per_page))),
        },
    )


@router.get("/wc/v3/orders")
@router.get("/wc/v2/orders")
async def list_orders(
    db: DbDep,
    _key: WcAuthDep,
    page: int = Query(default=1),
    per_page: int = Query(default=10),
    status: str | None = Query(default=None),
) -> JSONResponse:
    items, total = await service.list_orders(db, page=page, per_page=per_page, status=status)
    return _paged({}, items, total, per_page or 10)


@router.get("/wc/v3/orders/{wc_id}")
@router.get("/wc/v2/orders/{wc_id}")
async def get_order(wc_id: int, db: DbDep, _key: WcAuthDep) -> dict:
    order = await service.get_order_by_wc_id(db, wc_id)
    if not order:
        raise NotFoundError("Pedido não encontrado.")
    return await service.order_out(db, order)


@router.put("/wc/v3/orders/{wc_id}")
@router.put("/wc/v2/orders/{wc_id}")
async def update_order(wc_id: int, patch: dict, db: DbDep, _key: WcAuthDep) -> dict:
    order = await service.get_order_by_wc_id(db, wc_id)
    if not order:
        raise NotFoundError("Pedido não encontrado.")
    await service.update_order(db, order, patch)
    await db.commit()
    # `orders_service.transition` já fez o commit dela e deixa os atributos
    # do objeto expirados -- rebusca pra montar a saída sem cair em lazy
    # load síncrono fora de contexto async (MissingGreenlet).
    order = await service.get_order_by_wc_id(db, wc_id)
    return await service.order_out(db, order)


# --------------------------------------------------------------- produtos

@router.get("/wc/v3/products")
@router.get("/wc/v2/products")
async def list_products(
    db: DbDep,
    _key: WcAuthDep,
    page: int = Query(default=1),
    per_page: int = Query(default=10),
) -> JSONResponse:
    items, total = await service.list_products(db, page=page, per_page=per_page)
    return _paged({}, items, total, per_page or 10)


@router.get("/wc/v3/products/{wc_id}")
@router.get("/wc/v2/products/{wc_id}")
async def get_product(wc_id: int, db: DbDep, _key: WcAuthDep) -> dict:
    product = await service.get_product_by_wc_id(db, wc_id)
    if not product:
        raise NotFoundError("Produto não encontrado.")
    return await service.product_out(db, product)


@router.put("/wc/v3/products/{wc_id}")
@router.put("/wc/v2/products/{wc_id}")
async def update_product(wc_id: int, patch: dict, db: DbDep, _key: WcAuthDep) -> dict:
    product = await service.get_product_by_wc_id(db, wc_id)
    if not product:
        raise NotFoundError("Produto não encontrado.")
    product = await service.update_product(db, product, patch)
    await db.commit()
    return await service.product_out(db, product)


@router.get("/wc/v3/products/{wc_id}/variations")
@router.get("/wc/v2/products/{wc_id}/variations")
async def list_variations(wc_id: int, db: DbDep, _key: WcAuthDep) -> list[dict]:
    product = await service.get_product_by_wc_id(db, wc_id)
    if not product:
        raise NotFoundError("Produto não encontrado.")
    return await service.list_variants_out(db, product)


@router.get("/wc/v3/products/{wc_id}/variations/{variation_id}")
@router.get("/wc/v2/products/{wc_id}/variations/{variation_id}")
async def get_variation(wc_id: int, variation_id: int, db: DbDep, _key: WcAuthDep) -> dict:
    product = await service.get_product_by_wc_id(db, wc_id)
    if not product:
        raise NotFoundError("Produto não encontrado.")
    variant = await service.get_variant_by_wc_id(db, product.id, variation_id)
    if not variant:
        raise NotFoundError("Variação não encontrada.")
    return await service.variant_out(db, product, variant)


@router.put("/wc/v3/products/{wc_id}/variations/{variation_id}")
@router.put("/wc/v2/products/{wc_id}/variations/{variation_id}")
async def update_variation(
    wc_id: int, variation_id: int, patch: dict, db: DbDep, _key: WcAuthDep
) -> dict:
    product = await service.get_product_by_wc_id(db, wc_id)
    if not product:
        raise NotFoundError("Produto não encontrado.")
    variant = await service.get_variant_by_wc_id(db, product.id, variation_id)
    if not variant:
        raise NotFoundError("Variação não encontrada.")
    variant = await service.update_variant(db, variant, patch)
    await db.commit()
    return await service.variant_out(db, product, variant)


# --------------------------------------------------------------- webhooks

@router.post("/wc/v3/webhooks")
@router.post("/wc/v2/webhooks")
async def create_webhook(payload: dict, db: DbDep, _key: WcAuthDep) -> dict:
    row = await service.create_webhook(db, payload)
    await db.commit()
    return service.webhook_out(row)


@router.get("/wc/v3/webhooks")
@router.get("/wc/v2/webhooks")
async def list_webhooks(db: DbDep, _key: WcAuthDep) -> list[dict]:
    rows = await service.list_webhooks(db)
    return [service.webhook_out(r) for r in rows]


@router.get("/wc/v3/webhooks/{webhook_id}")
@router.get("/wc/v2/webhooks/{webhook_id}")
async def get_webhook(webhook_id: int, db: DbDep, _key: WcAuthDep) -> dict:
    row = await service.get_webhook(db, webhook_id)
    return service.webhook_out(row)


@router.put("/wc/v3/webhooks/{webhook_id}")
@router.put("/wc/v2/webhooks/{webhook_id}")
async def update_webhook(webhook_id: int, patch: dict, db: DbDep, _key: WcAuthDep) -> dict:
    row = await service.update_webhook(db, webhook_id, patch)
    await db.commit()
    return service.webhook_out(row)


@router.delete("/wc/v3/webhooks/{webhook_id}")
@router.delete("/wc/v2/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: int, db: DbDep, _key: WcAuthDep) -> dict:
    row = await service.get_webhook(db, webhook_id)
    out = service.webhook_out(row)
    await service.delete_webhook(db, webhook_id)
    await db.commit()
    return out
