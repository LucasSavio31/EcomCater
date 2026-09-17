"""Regra de negócio do módulo `upseller` -- só a direção "UP Seller ->
loja" existe (API pública deles só lê estoque; não tem pedidos/produtos)."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.products.models import ProductVariant
from app.modules.upseller.client import UpSellerClient, UpSellerError
from app.modules.upseller.config import UpSellerConfig


async def load_config(db: AsyncSession) -> UpSellerConfig:
    from app.modules.admin.models import ModuleRow

    row = await db.get(ModuleRow, "upseller")
    raw = dict(row.config_json) if row and row.config_json else {}
    return UpSellerConfig(**raw)


async def save_config(db: AsyncSession, patch: dict) -> UpSellerConfig:
    from app.modules.admin.models import ModuleRow

    row = await db.get(ModuleRow, "upseller")
    current = dict(row.config_json) if row and row.config_json else {}
    for k, v in patch.items():
        if v is not None:
            current[k] = v
    cfg = UpSellerConfig(**current)
    if row is None:
        row = ModuleRow(slug="upseller", enabled=True, config_json=cfg.model_dump())
        db.add(row)
    else:
        row.config_json = cfg.model_dump()
    row.updated_at = datetime.now(UTC)
    await db.flush()
    return cfg


def is_connected(cfg: UpSellerConfig) -> bool:
    return bool(cfg.client_id and cfg.api_token)


async def get_client(db: AsyncSession) -> UpSellerClient:
    cfg = await load_config(db)
    if not is_connected(cfg):
        raise DomainError("UP Seller não configurada. Informe Client ID e API Token.", code="upseller_not_connected")
    return UpSellerClient(client_id=cfg.client_id, api_token=cfg.api_token)


async def test_connection(db: AsyncSession) -> dict:
    cfg = await load_config(db)
    if not is_connected(cfg):
        return {"ok": False, "message": "Ainda não configurada."}
    try:
        client = UpSellerClient(client_id=cfg.client_id, api_token=cfg.api_token)
        warehouses = await client.list_warehouses(page_no=1, page_size=1)
    except UpSellerError as exc:
        return {"ok": False, "message": str(exc)}
    total = warehouses.get("total", 0)
    return {"ok": True, "message": f"Conectado -- {total} armazém(ns) na conta."}


async def list_warehouses(db: AsyncSession) -> list[dict]:
    client = await get_client(db)
    try:
        return await client.all_warehouses()
    except UpSellerError as exc:
        raise DomainError(str(exc), code="upseller_error") from exc


async def sync_stock(db: AsyncSession) -> dict:
    """Busca o estoque de todo SKU em todo armazém da UP Seller, soma por
    SKU (estoque total = soma entre armazéns) e aplica em `ProductVariant`
    cujo `sku` bate exatamente. SKU sem correspondência é ignorado (não é
    erro -- é normal ter SKU só de um lado)."""
    client = await get_client(db)
    try:
        warehouses = await client.all_warehouses()
        totals: dict[str, int] = {}
        for wh in warehouses:
            wh_id = wh.get("warehouseId")
            if not wh_id:
                continue
            for row in await client.all_warehouse_skus(str(wh_id)):
                sku = row.get("skuId")
                qty = row.get("quantity")
                if not sku or qty is None:
                    continue
                totals[str(sku)] = totals.get(str(sku), 0) + int(qty)
    except UpSellerError as exc:
        raise DomainError(str(exc), code="upseller_error") from exc

    updated = 0
    if totals:
        variants = list(
            await db.scalars(select(ProductVariant).where(ProductVariant.sku.in_(totals.keys())))
        )
        for v in variants:
            v.stock_qty = totals[v.sku]
            updated += 1
    summary = f"{len(totals)} SKU(s) na UP Seller, {updated} atualizado(s) na loja"
    await save_config(
        db, {"last_sync_at": datetime.now(UTC).isoformat(), "last_sync_summary": summary}
    )
    await db.commit()
    return {"skus_found": len(totals), "variants_updated": updated}
