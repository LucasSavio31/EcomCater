"""Regra de negócio do módulo `woocommerce` -- chaves da API, leitura/escrita
de pedidos e produtos no formato WooCommerce, e disparo de webhooks."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError, ValidationError
from app.core.security import hash_password
from app.modules.categories.models import Category
from app.modules.orders import service as orders_service
from app.modules.orders.models import Order
from app.modules.products.models import Product, ProductImage, ProductVariant, VariantOptionValue
from app.modules.woocommerce import mapping
from app.modules.woocommerce.models import WEBHOOK_TOPICS, WooKey, WooWebhook
from app.shared.storage import storage

logger = logging.getLogger("woocommerce.service")

_MAX_PER_PAGE = 100


def _clamp_page(page: int | None) -> int:
    return max(1, page or 1)


def _clamp_per_page(per_page: int | None) -> int:
    return min(_MAX_PER_PAGE, max(1, per_page or 10))


# --------------------------------------------------------------------- keys

async def generate_key(db: AsyncSession, *, description: str | None, permission: str) -> tuple[WooKey, str, str]:
    consumer_key = "ck_" + secrets.token_hex(20)
    consumer_secret = "cs_" + secrets.token_hex(20)
    row = WooKey(
        consumer_key=consumer_key,
        consumer_secret_hash=hash_password(consumer_secret),
        description=description,
        permission=permission,
    )
    db.add(row)
    await db.flush()
    return row, consumer_key, consumer_secret


async def list_keys(db: AsyncSession) -> list[WooKey]:
    return list(await db.scalars(select(WooKey).order_by(WooKey.created_at)))


async def revoke_key(db: AsyncSession, key_id: str) -> None:
    row = await db.get(WooKey, key_id)
    if not row:
        raise NotFoundError("Chave não encontrada.")
    await db.delete(row)
    await db.flush()


# ------------------------------------------------------------------ pedidos

async def _order_product_wc_ids(db: AsyncSession, order: Order) -> dict[str, int]:
    pids = {it.product_id for it in order.items if it.product_id}
    if not pids:
        return {}
    rows = await db.execute(select(Product.id, Product.wc_id).where(Product.id.in_(pids)))
    return {str(pid): wc_id for pid, wc_id in rows}


async def _order_out(db: AsyncSession, order: Order) -> dict:
    product_wc_ids = await _order_product_wc_ids(db, order)
    return mapping.order_to_wc(order, product_wc_ids=product_wc_ids)


async def list_orders(
    db: AsyncSession, *, page: int | None, per_page: int | None, status: str | None,
) -> tuple[list[dict], int]:
    page = _clamp_page(page)
    per_page = _clamp_per_page(per_page)
    stmt = select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc())
    if status:
        our_status = mapping.WC_STATUS_TO_ORDER.get(status)
        if our_status:
            stmt = stmt.where(Order.status == our_status)
    total = len(list(await db.scalars(stmt)))
    rows = list(
        await db.scalars(stmt.offset((page - 1) * per_page).limit(per_page))
    )
    return [await _order_out(db, o) for o in rows], total


async def get_order_by_wc_id(db: AsyncSession, wc_id: int) -> Order | None:
    return await db.scalar(
        select(Order).where(Order.wc_id == wc_id).options(selectinload(Order.items))
    )


async def order_out(db: AsyncSession, order: Order) -> dict:
    return await _order_out(db, order)



# Régua de avanço (nunca retrocede), mesmo espírito de `_ORDER_STATUS_RANK`
# em `shipping/service.py` -- duplicada aqui de propósito (módulo
# independente, sem acoplar num helper privado de outro módulo).
_STATUS_RANK = {
    "pending_payment": 0, "paid": 1, "processing": 2,
    "tracking_available": 3, "shipped": 4, "delivered": 5,
}


async def update_order(db: AsyncSession, order: Order, patch: dict) -> Order:
    status = patch.get("status")
    if status:
        new_status = mapping.WC_STATUS_TO_ORDER.get(status)
        if not new_status:
            raise ValidationError(f"Status do WooCommerce desconhecido: {status}.")
        await orders_service.transition(
            db, order, new_status, actor_type="admin",
            message="Atualizado via integração WooCommerce (ERP).",
        )
    # rastreio, se vier em meta_data (_tracking_number / _tracking_url) --
    # convenção do plugin de rastreio mais comum no ecossistema WooCommerce
    # (é assim que a Frenet, por exemplo, devolve o rastreio pra loja depois
    # de puxar o pedido por aqui -- ela não tem uma API própria de etiqueta
    # pra contas comuns, integra via WooCommerce mesmo).
    meta = {m.get("key"): m.get("value") for m in patch.get("meta_data") or []}
    tracking = meta.get("_tracking_number")
    if tracking:
        svc = dict(order.shipping_service_json or {})
        changed = svc.get("tracking_code") != tracking
        svc["tracking_code"] = tracking
        if meta.get("_tracking_url"):
            svc["tracking_url"] = meta["_tracking_url"]
        order.shipping_service_json = svc
        await db.flush()
        # rastreio chegou = "rastreio disponível" pro cliente -- mesma régua
        # de avanço automático que o Melhor Envio/Frenet nativos usam (nunca
        # regride um pedido que já está mais avançado, ex. já "shipped"; e só
        # mexe em pedido já pago -- rastreio num pedido ainda não pago não
        # deveria empurrar status nenhum).
        if (
            changed
            and order.status in {"paid", "processing"}
            and _STATUS_RANK.get("tracking_available", 0) > _STATUS_RANK.get(order.status, 99)
        ):
            await orders_service.transition(
                db, order, "tracking_available", actor_type="admin",
                message="Rastreio recebido via integração WooCommerce (ERP).",
            )
    return order


# ----------------------------------------------------------------- produtos

async def _primary_image_url(db: AsyncSession, product_id) -> str | None:
    img = await db.scalar(
        select(ProductImage)
        .where(ProductImage.product_id == product_id, ProductImage.variant_id.is_(None))
        .order_by(ProductImage.is_primary.desc(), ProductImage.position)
        .limit(1)
    )
    return storage.url(img.medium_key) if img else None


async def _category_name(db: AsyncSession, category_id) -> str | None:
    if not category_id:
        return None
    cat = await db.get(Category, category_id)
    return cat.name if cat else None


async def _variant_attrs(variant: ProductVariant) -> dict[str, str]:
    return {v.option_type.name: v.value for v in variant.option_values}


async def _product_out(db: AsyncSession, product: Product) -> dict:
    variants = list(
        await db.scalars(
            select(ProductVariant)
            .where(ProductVariant.product_id == product.id)
            .options(selectinload(ProductVariant.option_values).selectinload(VariantOptionValue.option_type))
            .order_by(ProductVariant.position)
        )
    )
    image_url = await _primary_image_url(db, product.id)
    category_name = await _category_name(db, product.category_id)
    return mapping.product_to_wc(
        product,
        variants=variants,
        primary_image_url=image_url,
        category_name=category_name,
        variation_ids=[v.wc_id for v in variants],
    )


async def list_products(db: AsyncSession, *, page: int | None, per_page: int | None) -> tuple[list[dict], int]:
    page = _clamp_page(page)
    per_page = _clamp_per_page(per_page)
    stmt = select(Product).order_by(Product.created_at.desc())
    total = len(list(await db.scalars(stmt)))
    rows = list(await db.scalars(stmt.offset((page - 1) * per_page).limit(per_page)))
    return [await _product_out(db, p) for p in rows], total


async def get_product_by_wc_id(db: AsyncSession, wc_id: int) -> Product | None:
    return await db.scalar(select(Product).where(Product.wc_id == wc_id))


async def product_out(db: AsyncSession, product: Product) -> dict:
    return await _product_out(db, product)


async def update_product(db: AsyncSession, product: Product, patch: dict) -> Product:
    if "regular_price" in patch and patch["regular_price"] not in (None, ""):
        product.price_cents = round(float(patch["regular_price"]) * 100)
    if "sale_price" in patch and patch["sale_price"] not in (None, ""):
        product.compare_at_price_cents = product.price_cents
        product.price_cents = round(float(patch["sale_price"]) * 100)
    if "stock_quantity" in patch and patch["stock_quantity"] is not None:
        # No WooCommerce de verdade, `stock_quantity` no endpoint do produto
        # só vale pra produto SIMPLES (sem variação) -- produto variável
        # gerencia estoque por variação (`/variations/{id}`). Com uma única
        # variação (caso comum aqui: produto de 1 numeração só), aplica nela;
        # com mais de uma, ignora -- a escrita tem que vir por variação.
        variants = list(
            await db.scalars(select(ProductVariant).where(ProductVariant.product_id == product.id))
        )
        if len(variants) == 1:
            variants[0].stock_qty = int(patch["stock_quantity"])
    await db.flush()
    return product


# --------------------------------------------------------------- variações

async def get_variant_by_wc_id(db: AsyncSession, product_id, variation_wc_id: int) -> ProductVariant | None:
    return await db.scalar(
        select(ProductVariant)
        .where(ProductVariant.product_id == product_id, ProductVariant.wc_id == variation_wc_id)
        .options(selectinload(ProductVariant.option_values).selectinload(VariantOptionValue.option_type))
    )


async def variant_out(db: AsyncSession, product: Product, variant: ProductVariant) -> dict:
    attrs = await _variant_attrs(variant)
    image_url = None
    img = await db.scalar(
        select(ProductImage)
        .where(ProductImage.variant_id == variant.id)
        .order_by(ProductImage.position)
        .limit(1)
    )
    if img:
        image_url = storage.url(img.medium_key)
    return mapping.variation_to_wc(product, variant, image_url=image_url, attrs=attrs)


async def list_variants_out(db: AsyncSession, product: Product) -> list[dict]:
    variants = list(
        await db.scalars(
            select(ProductVariant)
            .where(ProductVariant.product_id == product.id)
            .options(selectinload(ProductVariant.option_values).selectinload(VariantOptionValue.option_type))
            .order_by(ProductVariant.position)
        )
    )
    return [await variant_out(db, product, v) for v in variants]


async def update_variant(db: AsyncSession, variant: ProductVariant, patch: dict) -> ProductVariant:
    if "stock_quantity" in patch and patch["stock_quantity"] is not None:
        variant.stock_qty = int(patch["stock_quantity"])
    if "regular_price" in patch and patch["regular_price"] not in (None, ""):
        variant.price_cents = round(float(patch["regular_price"]) * 100)
    if "sale_price" in patch and patch["sale_price"] not in (None, ""):
        variant.compare_at_price_cents = variant.price_cents
        variant.price_cents = round(float(patch["sale_price"]) * 100)
    await db.flush()
    return variant


# --------------------------------------------------------------- webhooks

async def create_webhook(db: AsyncSession, payload: dict) -> WooWebhook:
    topic = payload.get("topic")
    if topic not in WEBHOOK_TOPICS:
        raise ValidationError(
            f"Tópico não suportado: {topic!r}. Use um de: {', '.join(WEBHOOK_TOPICS)}."
        )
    delivery_url = payload.get("delivery_url")
    if not delivery_url:
        raise ValidationError("delivery_url é obrigatório.")
    row = WooWebhook(
        name=payload.get("name") or topic,
        topic=topic,
        delivery_url=delivery_url,
        secret=payload.get("secret") or secrets.token_urlsafe(24),
        status=payload.get("status") or "active",
    )
    db.add(row)
    await db.flush()
    return row


async def list_webhooks(db: AsyncSession) -> list[WooWebhook]:
    return list(await db.scalars(select(WooWebhook).order_by(WooWebhook.id)))


async def get_webhook(db: AsyncSession, webhook_id: int) -> WooWebhook:
    row = await db.get(WooWebhook, webhook_id)
    if not row:
        raise NotFoundError("Webhook não encontrado.")
    return row


async def update_webhook(db: AsyncSession, webhook_id: int, patch: dict) -> WooWebhook:
    row = await get_webhook(db, webhook_id)
    for field in ("name", "delivery_url", "status", "secret"):
        if patch.get(field):
            setattr(row, field, patch[field])
    row.updated_at = datetime.now(UTC)
    await db.flush()
    return row


async def delete_webhook(db: AsyncSession, webhook_id: int) -> None:
    row = await get_webhook(db, webhook_id)
    await db.delete(row)
    await db.flush()


def webhook_out(row: WooWebhook) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "status": row.status,
        "topic": row.topic,
        "delivery_url": row.delivery_url,
        "date_created": row.created_at.isoformat() if row.created_at else None,
        "date_modified": row.updated_at.isoformat() if row.updated_at else None,
    }


def _sign(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


async def deliver(db: AsyncSession, *, topic: str, order: Order) -> None:
    """Dispara o webhook pros assinantes ativos daquele tópico -- é a
    direção "loja -> ERP" da integração, no formato de verdade do
    WooCommerce (headers `X-WC-Webhook-*` + assinatura HMAC)."""
    hooks = list(
        await db.scalars(
            select(WooWebhook).where(WooWebhook.topic == topic, WooWebhook.status == "active")
        )
    )
    if not hooks:
        return
    payload = await _order_out(db, order)
    body = json.dumps(payload).encode()
    for hook in hooks:
        headers = {
            "Content-Type": "application/json",
            "X-WC-Webhook-Topic": topic,
            "X-WC-Webhook-Resource": "order",
            "X-WC-Webhook-Event": topic.split(".", 1)[1] if "." in topic else topic,
            "X-WC-Webhook-Signature": _sign(hook.secret, body),
            "X-WC-Webhook-ID": str(hook.id),
            "X-WC-Webhook-Delivery-ID": secrets.token_hex(8),
        }
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                resp = await c.post(hook.delivery_url, content=body, headers=headers)
            if resp.status_code >= 400:
                logger.warning(
                    "webhook %s (%s) -> %s: HTTP %s", hook.id, topic, hook.delivery_url, resp.status_code
                )
        except httpx.HTTPError as exc:
            logger.warning("webhook %s (%s) falhou: %s", hook.id, topic, exc)
