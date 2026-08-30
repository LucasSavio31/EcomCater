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
            is_color=ot.get("is_color", False),
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


async def _get_type(db: AsyncSession, product_id: str, type_id: str) -> VariantOptionType:
    ot = await db.scalar(
        select(VariantOptionType)
        .where(VariantOptionType.id == _uuid(type_id))
        .options(selectinload(VariantOptionType.values))
    )
    if not ot or str(ot.product_id) != str(_uuid(product_id)):
        raise NotFoundError("Eixo de opção não encontrado.")
    return ot


async def patch_option_type(
    db: AsyncSession, product_id: str, type_id: str, data: dict
) -> Product:
    """Ajusta nome/flags de um eixo. Permitido mesmo com variações (não mexe em SKU)."""
    ot = await _get_type(db, product_id, type_id)
    if data.get("name") is not None and str(data["name"]).strip():
        ot.name = str(data["name"]).strip()
    if "is_size" in data and data["is_size"] is not None:
        ot.is_size = bool(data["is_size"])
    if "is_color" in data and data["is_color"] is not None:
        ot.is_color = bool(data["is_color"])
    await db.flush()
    return await _get_product(db, product_id)


async def add_option_value(
    db: AsyncSession, product_id: str, type_id: str, value: str
) -> Product:
    """Inclui um novo valor num eixo existente (funciona mesmo com variações)."""
    ot = await _get_type(db, product_id, type_id)
    label = (value or "").strip()
    if not label:
        raise ValidationError("Informe o valor.")
    if any(v.value.lower() == label.lower() for v in ot.values):
        raise ConflictError(f"O valor '{label}' já existe neste eixo.")
    pos = max((v.position for v in ot.values), default=-1) + 1
    db.add(VariantOptionValue(option_type_id=ot.id, value=label, position=pos))
    await db.flush()
    return await _get_product(db, product_id)


async def update_option_value(
    db: AsyncSession, product_id: str, value_id: str, data: dict
) -> Product:
    """Renomeia um valor e/ou define a imagem (miniatura de cor)."""
    val = await db.get(VariantOptionValue, _uuid(value_id))
    if not val:
        raise NotFoundError("Valor de opção não encontrado.")
    ot = await _get_type(db, product_id, str(val.option_type_id))  # valida o produto
    if data.get("value") is not None and str(data["value"]).strip():
        val.value = str(data["value"]).strip()
    if "image_id" in data:
        img_id = data["image_id"]
        if img_id:
            from app.modules.products.models import ProductImage

            img = await db.get(ProductImage, _uuid(img_id))
            if not img or str(img.product_id) != str(_uuid(product_id)):
                raise ValidationError("Imagem não pertence a este produto.")
            val.image_id = img.id
        else:
            val.image_id = None
    await db.flush()
    _ = ot
    return await _get_product(db, product_id)


async def delete_option_value(db: AsyncSession, product_id: str, value_id: str) -> Product:
    """Exclui um valor. Bloqueado se alguma variação já o usa."""
    val = await db.get(VariantOptionValue, _uuid(value_id))
    if not val:
        raise NotFoundError("Valor de opção não encontrado.")
    await _get_type(db, product_id, str(val.option_type_id))  # valida o produto
    used = await db.scalar(
        select(ProductVariantOption.variant_id)
        .where(ProductVariantOption.option_value_id == val.id)
        .limit(1)
    )
    if used:
        raise ConflictError(
            "Este valor está em uso por uma variação. Exclua a variação primeiro."
        )
    await db.delete(val)
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

    for f in ("sku", "price_cents", "compare_at_price_cents", "weight_grams", "barcode", "is_active", "position"):
        if f in data and data[f] is not None:
            setattr(variant, f, data[f])
    # stock_qty: aceita None de propósito (== estoque ilimitado)
    if "stock_qty" in data:
        variant.stock_qty = data["stock_qty"]
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
    if variant.stock_qty is None:  # ilimitado: nada a ajustar
        return variant
    variant.stock_qty = max(0, variant.stock_qty + delta)
    return variant
