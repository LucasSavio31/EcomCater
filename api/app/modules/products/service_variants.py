"""Gestão de eixos de opção e variações (SKU) de um produto."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.modules.products.models import (
    Product,
    ProductVariant,
    ProductVariantOption,
    VariantOptionType,
    VariantOptionValue,
)


def _uuid(v: str | uuid.UUID) -> uuid.UUID:
    if isinstance(v, uuid.UUID):
        return v
    try:
        return uuid.UUID(v)
    except ValueError as exc:
        raise ValidationError("id inválido") from exc


async def _get_product(db: AsyncSession, product_id: str) -> Product:
    p = await db.scalar(
        select(Product)
        .where(Product.id == _uuid(product_id))
        .options(
            selectinload(Product.option_types).selectinload(VariantOptionType.values),
            selectinload(Product.variants).selectinload(ProductVariant.option_values),
        )
    )
    if not p:
        raise NotFoundError("Produto não encontrado.")
    return p


async def replace_option_types(db: AsyncSession, product_id: str, option_types: list[dict]) -> Product:
    """Substitui os eixos de opção. Só permitido se não houver variações ainda
    (ou elas são removidas junto — cuidado)."""
    product = await _get_product(db, product_id)
    if product.variants:
        raise ConflictError("Remova as variações antes de alterar os eixos de opção.")
    for ot in list(product.option_types):
        await db.delete(ot)
    await db.flush()
    for i, ot in enumerate(option_types):
        row = VariantOptionType(
            product_id=product.id,
            name=ot["name"],
            is_size=ot.get("is_size", False),
            position=ot.get("position", i),
        )
        db.add(row)
        await db.flush()
        for j, val in enumerate(ot.get("values", [])):
            db.add(
                VariantOptionValue(
                    option_type_id=row.id,
                    value=val["value"],
                    position=val.get("position", j),
                )
            )
    await db.flush()
    return await _get_product(db, product_id)


async def upsert_variant(db: AsyncSession, product_id: str, data: dict, variant_id: str | None = None) -> ProductVariant:
    product = await _get_product(db, product_id)
    valid_value_ids = {
        v.id for ot in product.option_types for v in ot.values
    }
    chosen = [_uuid(x) for x in data.get("option_value_ids", [])]
    for c in chosen:
        if c not in valid_value_ids:
            raise ValidationError("option_value_id não pertence a este produto.")

    # uma variação por combinação de eixos
    if product.option_types and len(chosen) != len(product.option_types):
        raise ValidationError(
            f"A variação deve ter exatamente {len(product.option_types)} valor(es) de opção."
        )

    if variant_id:
        variant = await db.get(ProductVariant, _uuid(variant_id))
        if not variant or variant.product_id != product.id:
            raise NotFoundError("Variação não encontrada.")
    else:
        dup = await db.scalar(select(ProductVariant).where(ProductVariant.sku == data["sku"]))
        if dup:
            raise ConflictError(f"SKU já existe: {data['sku']}")
        variant = ProductVariant(product_id=product.id)
        db.add(variant)

    for f in ("sku", "price_cents", "compare_at_price_cents", "stock_qty", "weight_grams", "barcode", "is_active", "position"):
        if f in data and data[f] is not None:
            setattr(variant, f, data[f])
    await db.flush()

    # sincroniza opções da variação
    for link in await db.scalars(
        select(ProductVariantOption).where(ProductVariantOption.variant_id == variant.id)
    ):
        await db.delete(link)
    for vid in chosen:
        db.add(ProductVariantOption(variant_id=variant.id, option_value_id=vid))
    await db.flush()
    return variant


async def delete_variant(db: AsyncSession, product_id: str, variant_id: str) -> None:
    variant = await db.get(ProductVariant, _uuid(variant_id))
    if not variant or str(variant.product_id) != str(_uuid(product_id)):
        raise NotFoundError("Variação não encontrada.")
    from app.modules.orders.models import OrderItem

    used = await db.scalar(select(OrderItem.id).where(OrderItem.variant_id == variant.id).limit(1))
    if used:
        raise ConflictError("Variação já usada em pedidos — desative em vez de excluir.")
    await db.delete(variant)


async def adjust_stock(db: AsyncSession, variant_id: str, delta: int) -> ProductVariant:
    variant = await db.get(ProductVariant, _uuid(variant_id))
    if not variant:
        raise NotFoundError("Variação não encontrada.")
    variant.stock_qty = max(0, variant.stock_qty + delta)
    return variant
