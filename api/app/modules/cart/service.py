"""Regra de negócio do módulo `cart` — fonte única da verdade do carrinho.

Estende-se nas fases seguintes: F5 (cupom + frete nos totais), F6 (estado de
checkout). Mantido com dono único.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError, ValidationError
from app.core.redis import redis_client
from app.modules.cart.models import Cart, CartItem
from app.modules.products.models import Product, ProductVariant
from app.modules.products.service import variant_price
from app.modules.theme.models import ThemeSettings

CART_TTL_DAYS = 30
_REDIS_PREFIX = "cart:tok:"


def _uuid(v: str | uuid.UUID) -> uuid.UUID:
    if isinstance(v, uuid.UUID):
        return v
    try:
        return uuid.UUID(v)
    except ValueError as exc:
        raise ValidationError("id inválido") from exc


def new_token() -> str:
    return secrets.token_urlsafe(24)


async def _touch_redis(token: str, cart_id: uuid.UUID) -> None:
    try:
        await redis_client.set(
            f"{_REDIS_PREFIX}{token}", str(cart_id), ex=CART_TTL_DAYS * 86400
        )
    except Exception:  # noqa: BLE001 - Redis indisponível não deve quebrar o carrinho
        pass


async def _load(db: AsyncSession, cart_id: uuid.UUID) -> Cart | None:
    return await db.scalar(
        select(Cart)
        .where(Cart.id == cart_id)
        .options(selectinload(Cart.items))
        .execution_options(populate_existing=True)  # relê `items` mesmo se já em cache
    )


async def get_or_create(
    db: AsyncSession, *, token: str | None, user_id: str | None
) -> Cart:
    """Resolve o carrinho: usuário logado tem precedência; senão usa o token."""
    cart: Cart | None = None

    if user_id:
        cart = await db.scalar(
            select(Cart).where(Cart.user_id == _uuid(user_id)).options(selectinload(Cart.items))
        )

    if cart is None and token:
        cart = await db.scalar(
            select(Cart).where(Cart.session_token == token).options(selectinload(Cart.items))
        )
        if cart and user_id and cart.user_id is None:
            cart.user_id = _uuid(user_id)

    if cart is None:
        cart = Cart(
            user_id=_uuid(user_id) if user_id else None,
            session_token=token or new_token(),
            expires_at=datetime.now(UTC) + timedelta(days=CART_TTL_DAYS),
        )
        db.add(cart)
        await db.flush()

    cart.expires_at = datetime.now(UTC) + timedelta(days=CART_TTL_DAYS)
    await db.flush()
    await _touch_redis(cart.session_token, cart.id)

    # garante `items` carregado — acessá-lo sem eager-load quebra no async
    # (`MissingGreenlet`), e o carrinho recém-criado não passou pelo selectinload.
    if "items" not in cart.__dict__:
        cart = await _load(db, cart.id) or cart
    return cart


async def _get_variant(db: AsyncSession, variant_id: str) -> tuple[Product, ProductVariant]:
    variant = await db.scalar(
        select(ProductVariant)
        .where(ProductVariant.id == _uuid(variant_id))
        .options(selectinload(ProductVariant.option_values))
    )
    if not variant or not variant.is_active:
        raise NotFoundError("Variação indisponível.")
    product = await db.get(Product, variant.product_id)
    if not product or product.status != "active":
        raise NotFoundError("Produto indisponível.")
    return product, variant


async def add_item(db: AsyncSession, cart: Cart, variant_id: str, quantity: int) -> Cart:
    product, variant = await _get_variant(db, variant_id)
    existing = next((i for i in cart.items if str(i.variant_id) == str(variant.id)), None)
    desired = (existing.quantity if existing else 0) + quantity
    if variant.stock_qty is not None and desired > variant.stock_qty:
        raise ValidationError(
            f"Estoque insuficiente: restam {variant.stock_qty} unidade(s) de {product.name}."
        )
    price = variant_price(product, variant)
    if existing:
        existing.quantity = desired
        existing.unit_price_cents = price
    else:
        db.add(
            CartItem(
                cart_id=cart.id,
                product_id=product.id,
                variant_id=variant.id,
                quantity=quantity,
                unit_price_cents=price,
            )
        )
    await db.flush()
    return await _load(db, cart.id)  # type: ignore[return-value]


async def update_item(db: AsyncSession, cart: Cart, item_id: str, quantity: int) -> Cart:
    item = next((i for i in cart.items if str(i.id) == str(item_id)), None)
    if not item:
        raise NotFoundError("Item não encontrado no carrinho.")
    if quantity == 0:
        await db.delete(item)
    else:
        _, variant = await _get_variant(db, str(item.variant_id))
        if variant.stock_qty is not None and quantity > variant.stock_qty:
            raise ValidationError(f"Estoque insuficiente: restam {variant.stock_qty}.")
        item.quantity = quantity
    await db.flush()
    return await _load(db, cart.id)  # type: ignore[return-value]


async def remove_item(db: AsyncSession, cart: Cart, item_id: str) -> Cart:
    item = next((i for i in cart.items if str(i.id) == str(item_id)), None)
    if item:
        await db.delete(item)
        await db.flush()
    return await _load(db, cart.id)  # type: ignore[return-value]


async def set_zip(db: AsyncSession, cart: Cart, zip_code: str) -> Cart:
    cart.shipping_zip = zip_code
    cart.selected_shipping_json = None  # invalida frete escolhido
    await db.flush()
    return cart


async def apply_coupon(db: AsyncSession, cart: Cart, code: str) -> tuple[Cart, str | None]:
    """Valida e vincula o cupom. Retorna (cart, erro|None)."""
    from app.modules.promotions import service as promo

    try:
        coupon = await promo.validate_for_cart(db, code, cart)
    except ValidationError as exc:
        cart.coupon_id = None
        return cart, exc.message
    cart.coupon_id = coupon.id
    await db.flush()
    return cart, None


async def remove_coupon(db: AsyncSession, cart: Cart) -> Cart:
    cart.coupon_id = None
    await db.flush()
    return cart


async def select_shipping(db: AsyncSession, cart: Cart, service_id: str) -> Cart:
    """Fixa a opção de frete escolhida (a partir do cache de cotação da F5)."""
    from app.modules.shipping import service as shipping

    if not cart.shipping_zip:
        raise ValidationError("Informe o CEP antes de escolher o frete.")
    rate = await shipping.get_cached_rate(db, cart.shipping_zip, cart_items_signature(cart), service_id)
    if not rate:
        # recotar
        rates = await shipping.quote_for_cart(db, cart)
        rate = next((r for r in rates if str(r["id"]) == str(service_id)), None)
    if not rate:
        raise ValidationError("Opção de frete inválida — recalcule o frete.")
    cart.selected_shipping_json = rate
    await db.flush()
    return cart


def cart_items_signature(cart: Cart) -> str:
    parts = sorted(f"{i.variant_id}:{i.quantity}" for i in cart.items)
    return "|".join(parts)


# --------------------------------------------------------------------- totais
async def compute_totals(db: AsyncSession, cart: Cart) -> dict:
    items_total = sum(i.unit_price_cents * i.quantity for i in cart.items)
    items_count = sum(i.quantity for i in cart.items)

    discount = 0
    free_shipping_by_coupon = False
    if cart.coupon_id:
        from app.modules.promotions import service as promo

        discount, free_shipping_by_coupon = await promo.compute_discount(db, cart, items_total)

    shipping_cents = 0
    if cart.selected_shipping_json:
        shipping_cents = int(cart.selected_shipping_json.get("price_cents", 0))
    if free_shipping_by_coupon:
        shipping_cents = 0

    theme = await db.get(ThemeSettings, 1)
    threshold = theme.free_shipping_threshold_cents if theme else None
    remaining = None
    if threshold:
        if items_total - discount >= threshold:
            shipping_cents = 0
            remaining = 0
        else:
            remaining = threshold - (items_total - discount)

    grand = max(0, items_total - discount) + shipping_cents
    return {
        "items_count": items_count,
        "items_total_cents": items_total,
        "discount_cents": discount,
        "shipping_cents": shipping_cents,
        "grand_total_cents": grand,
        "free_shipping_threshold_cents": threshold,
        "free_shipping_remaining_cents": remaining,
    }


async def serialize(db: AsyncSession, cart: Cart, *, coupon_error: str | None = None) -> dict:
    from app.modules.promotions.models import Coupon

    items_out = []
    for i in sorted(cart.items, key=lambda x: x.created_at or datetime.now(UTC)):
        product, variant = await _get_variant_safe(db, i)
        current_price = variant_price(product, variant) if (product and variant) else i.unit_price_cents
        img = None
        if product:
            imgs = sorted(product.images, key=lambda x: (not x.is_primary, x.position))
            from app.shared.storage import storage

            img = storage.url(imgs[0].thumb_key) if imgs else None
        items_out.append(
            {
                "id": str(i.id),
                "product_id": str(i.product_id),
                "variant_id": str(i.variant_id),
                "product_name": product.name if product else "(indisponível)",
                "product_slug": product.slug if product else "",
                "variant_label": " / ".join(ov.value for ov in variant.option_values) if variant else None,
                "sku": variant.sku if variant else "",
                "image_url": img,
                "unit_price_cents": i.unit_price_cents,
                "quantity": i.quantity,
                "line_total_cents": i.unit_price_cents * i.quantity,
                "in_stock": bool(
                    variant and (variant.stock_qty is None or variant.stock_qty >= i.quantity)
                ),
                "max_qty": (
                    variant.stock_qty
                    if variant and variant.stock_qty is not None
                    else 999
                ),
                "price_changed": bool(variant and current_price != i.unit_price_cents),
            }
        )

    coupon_code = None
    if cart.coupon_id:
        c = await db.get(Coupon, cart.coupon_id)
        coupon_code = c.code if c else None

    return {
        "token": cart.session_token,
        "items": items_out,
        "totals": await compute_totals(db, cart),
        "coupon_code": coupon_code,
        "coupon_error": coupon_error,
        "shipping_zip": cart.shipping_zip,
        "selected_shipping": cart.selected_shipping_json,
    }


async def _get_variant_safe(db: AsyncSession, item: CartItem):
    variant = await db.scalar(
        select(ProductVariant)
        .where(ProductVariant.id == item.variant_id)
        .options(selectinload(ProductVariant.option_values))
    )
    product = None
    if variant:
        product = await db.scalar(
            select(Product).where(Product.id == variant.product_id).options(selectinload(Product.images))
        )
    return product, variant


# --------------------------------------------------------------------- merge no login
async def merge_guest_into_user(db: AsyncSession, *, guest_token: str, user_id: str) -> None:
    guest = await db.scalar(
        select(Cart).where(Cart.session_token == guest_token).options(selectinload(Cart.items))
    )
    if not guest or not guest.items:
        return
    user_cart = await db.scalar(
        select(Cart).where(Cart.user_id == _uuid(user_id)).options(selectinload(Cart.items))
    )
    if not user_cart:
        guest.user_id = _uuid(user_id)
        await db.flush()
        return
    by_variant = {str(i.variant_id): i for i in user_cart.items}
    for gi in guest.items:
        key = str(gi.variant_id)
        if key in by_variant:
            _, variant = await _get_variant_safe(db, gi)
            merged = by_variant[key].quantity + gi.quantity
            cap = (
                variant.stock_qty
                if variant and variant.stock_qty is not None
                else merged
            )
            by_variant[key].quantity = min(cap, merged)
        else:
            db.add(
                CartItem(
                    cart_id=user_cart.id,
                    product_id=gi.product_id,
                    variant_id=gi.variant_id,
                    quantity=gi.quantity,
                    unit_price_cents=gi.unit_price_cents,
                )
            )
    await db.delete(guest)
    await db.flush()


async def clear(db: AsyncSession, cart: Cart) -> None:
    """Esvazia o carrinho (usado após a criação do pedido — boleto/pix são
    assíncronos, então o carrinho não pode ficar preso até o pagamento)."""
    for item in list(cart.items):
        await db.delete(item)
    cart.coupon_id = None
    cart.selected_shipping_json = None
    await db.flush()


async def on_customer_logged_in(payload: dict) -> None:
    """Subscriber de `customer.logged_in` — o merge real precisa do token de
    convidado, que vem no header; o merge é disparado pelo router de auth."""
    _ = payload
