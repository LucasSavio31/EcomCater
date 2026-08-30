"""Regra de negócio do módulo `orders`.

Estoque: baixado na criação do pedido (evita oversell); restaurado no cancelamento.
Número do pedido: `AAAA-000123`, sequência por ano protegida por advisory lock.
Estende-se na F7 (finalização no pagamento).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.events import emit
from app.modules.orders.models import Order, OrderEvent, OrderItem
from app.modules.products.models import Product, ProductVariant
from app.shared.storage import storage

# transições permitidas (status do pedido)
_TRANSITIONS: dict[str, set[str]] = {
    "pending_payment": {"paid", "canceled"},
    "paid": {"processing", "canceled", "refunded"},
    "processing": {"shipped", "canceled", "refunded"},
    "shipped": {"delivered", "refunded"},
    "delivered": {"refunded"},
    "canceled": set(),
    "refunded": set(),
}


def _uuid(v: str | uuid.UUID) -> uuid.UUID:
    if isinstance(v, uuid.UUID):
        return v
    try:
        return uuid.UUID(v)
    except ValueError as exc:
        raise ValidationError("id inválido") from exc


async def generate_number(db: AsyncSession) -> str:
    year = datetime.now(UTC).year
    # serializa a numeração do ano corrente
    await db.execute(text("SELECT pg_advisory_xact_lock(:k)").bindparams(k=int(f"77{year}")))
    count = await db.scalar(
        select(func.count(Order.id)).where(Order.number.like(f"{year}-%"))
    )
    return f"{year}-{int(count or 0) + 1:06d}"


async def record_event(
    db: AsyncSession,
    order: Order,
    *,
    type: str,
    from_status: str | None = None,
    to_status: str | None = None,
    message: str | None = None,
    actor_type: str = "system",
    actor_id: str | None = None,
) -> None:
    db.add(
        OrderEvent(
            order_id=order.id,
            type=type,
            from_status=from_status,
            to_status=to_status,
            message=message,
            actor_type=actor_type,
            actor_id=actor_id,
            created_at=datetime.now(UTC),
        )
    )


async def create_from_cart(
    db: AsyncSession,
    cart,
    *,
    email: str,
    cpf: str | None,
    shipping_address: dict,
    billing_address: dict | None,
    customer_note: str | None,
    idempotency_key: str | None = None,
) -> Order:
    from app.modules.cart.service import compute_totals

    if not cart.items:
        raise ValidationError("Carrinho vazio.")

    if idempotency_key:
        existing = await db.scalar(
            select(Order).where(Order.shipping_service_json["idem"].astext == idempotency_key)
        )
        if existing:
            return existing

    # valida estoque e trava as variações
    variants: dict[uuid.UUID, ProductVariant] = {}
    for item in cart.items:
        v = await db.scalar(
            select(ProductVariant)
            .where(ProductVariant.id == item.variant_id)
            .with_for_update()
            .options(selectinload(ProductVariant.option_values))
        )
        if not v or not v.is_active:
            raise ConflictError("Um item do carrinho ficou indisponível.")
        if v.stock_qty is not None and v.stock_qty < item.quantity:
            product = await db.get(Product, v.product_id)
            raise ConflictError(f"Estoque insuficiente para {product.name if product else v.sku}.")
        variants[item.variant_id] = v

    totals = await compute_totals(db, cart)
    number = await generate_number(db)
    now = datetime.now(UTC)

    shipping_json = dict(cart.selected_shipping_json or {})
    if idempotency_key:
        shipping_json["idem"] = idempotency_key

    order = Order(
        number=number,
        user_id=cart.user_id,
        email=email,
        cpf=cpf,
        status="pending_payment",
        payment_status="pending",
        fulfillment_status="unfulfilled",
        items_total_cents=totals["items_total_cents"],
        discount_cents=totals["discount_cents"],
        shipping_cents=totals["shipping_cents"],
        grand_total_cents=totals["grand_total_cents"],
        coupon_id=cart.coupon_id,
        coupon_code=None,
        shipping_method=(cart.selected_shipping_json or {}).get("service"),
        shipping_service_json=shipping_json or None,
        shipping_address_json=shipping_address,
        billing_address_json=billing_address,
        customer_note=customer_note,
        placed_at=now,
    )
    db.add(order)
    await db.flush()

    if cart.coupon_id:
        from app.modules.promotions.models import Coupon

        c = await db.get(Coupon, cart.coupon_id)
        if c:
            order.coupon_code = c.code

    from app.modules.products.models import ProductImage

    for item in cart.items:
        v = variants[item.variant_id]
        product = await db.get(Product, v.product_id)
        if v.stock_qty is not None:
            v.stock_qty -= item.quantity  # baixa de estoque (ilimitado = não baixa)
        primary_img = await db.scalar(
            select(ProductImage)
            .where(ProductImage.product_id == v.product_id)
            .order_by(ProductImage.is_primary.desc(), ProductImage.position)
            .limit(1)
        )
        img_key = primary_img.medium_key if primary_img else None
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=v.product_id,
                variant_id=v.id,
                sku=v.sku,
                name=product.name if product else v.sku,
                variant_label=" / ".join(ov.value for ov in v.option_values) or None,
                supplier=product.supplier if product else None,
                image_key=img_key,
                unit_price_cents=item.unit_price_cents,
                quantity=item.quantity,
                total_cents=item.unit_price_cents * item.quantity,
            )
        )

    await record_event(db, order, type="created", to_status="pending_payment", message="Pedido criado")
    await db.flush()
    await emit("order.created", {"order_id": str(order.id), "number": order.number})
    return order


async def _load(db: AsyncSession, order_id: uuid.UUID) -> Order:
    order = await db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items), selectinload(Order.events))
    )
    if not order:
        raise NotFoundError("Pedido não encontrado.")
    return order


async def get_by_number(db: AsyncSession, number: str, *, email: str | None = None) -> Order:
    order = await db.scalar(
        select(Order)
        .where(Order.number == number)
        .options(selectinload(Order.items), selectinload(Order.events))
    )
    if not order or (email is not None and order.email.lower() != email.lower()):
        raise NotFoundError("Pedido não encontrado.")
    return order


async def transition(
    db: AsyncSession, order: Order, new_status: str, *, actor_type: str = "admin",
    actor_id: str | None = None, message: str | None = None,
) -> Order:
    if new_status == order.status:
        return order
    allowed = _TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise ValidationError(f"Transição inválida: {order.status} → {new_status}.")
    prev = order.status
    order.status = new_status

    if new_status == "paid":
        order.payment_status = "paid"
    elif new_status == "processing":
        order.fulfillment_status = "unfulfilled"
    elif new_status == "shipped":
        order.fulfillment_status = "fulfilled" if order.fulfillment_status == "fulfilled" else "partial"
    elif new_status == "delivered":
        order.fulfillment_status = "fulfilled"
    elif new_status in ("canceled", "refunded"):
        await _restore_stock(db, order)
        order.payment_status = "refunded" if new_status == "refunded" else order.payment_status

    await record_event(
        db, order, type="status_changed", from_status=prev, to_status=new_status,
        message=message, actor_type=actor_type, actor_id=actor_id,
    )
    await db.flush()
    await emit("order.status_changed", {"order_id": str(order.id), "status": new_status})
    return order


async def _restore_stock(db: AsyncSession, order: Order) -> None:
    for it in order.items:
        if it.variant_id:
            v = await db.get(ProductVariant, it.variant_id)
            if v and v.stock_qty is not None:
                v.stock_qty += it.quantity


async def finalize_paid(db: AsyncSession, order: Order) -> Order:
    """Chamado pelo webhook de pagamento quando o pagamento confirma."""
    if order.status == "pending_payment":
        await transition(db, order, "paid", actor_type="system", message="Pagamento confirmado")
        await transition(db, order, "processing", actor_type="system")
    # redime cupom (idempotente)
    if order.coupon_id:
        from app.modules.promotions import service as promo
        from app.modules.promotions.models import CouponRedemption

        exists = await db.scalar(
            select(CouponRedemption.id).where(CouponRedemption.order_id == order.id).limit(1)
        )
        if not exists:
            await promo.register_redemption(
                db,
                coupon_id=order.coupon_id,
                order_id=order.id,
                user_id=order.user_id,
                discount_cents=order.discount_cents,
            )
    await emit("order.paid", {"order_id": str(order.id), "number": order.number})
    return order


async def add_note(db: AsyncSession, order: Order, message: str, actor_id: str | None) -> None:
    await record_event(db, order, type="note", message=message, actor_type="admin", actor_id=actor_id)


# --------------------------------------------------------------------- serialização
def _variant_label_from_attrs(cor: str | None, numero: str | None) -> str | None:
    parts = [p.strip() for p in (cor, numero) if p and p.strip()]
    return " / ".join(parts) or None


def _item_out(it: OrderItem) -> dict:
    attrs = it.variant_attrs or {}
    return {
        "id": str(it.id),
        "sku": it.sku,
        "name": it.name,
        "product_id": str(it.product_id) if it.product_id else None,
        "variant_label": it.variant_label,
        "cor": attrs.get("cor"),
        "numero": attrs.get("numero"),
        # preenchidos por attach_variation_options() nas telas de detalhe
        "cor_options": [],
        "numero_options": [],
        "supplier": it.supplier,
        "image_url": storage.url(it.image_key) if it.image_key else None,
        "unit_price_cents": it.unit_price_cents,
        "quantity": it.quantity,
        "total_cents": it.total_cents,
    }


def to_out(order: Order) -> dict:
    return {
        "id": str(order.id),
        "number": order.number,
        "status": order.status,
        "payment_status": order.payment_status,
        "fulfillment_status": order.fulfillment_status,
        "email": order.email,
        "customer_name": _customer_name(order),
        "cpf": order.cpf,
        "items": [_item_out(i) for i in order.items],
        "items_total_cents": order.items_total_cents,
        "discount_cents": order.discount_cents,
        "shipping_cents": order.shipping_cents,
        "grand_total_cents": order.grand_total_cents,
        "coupon_code": order.coupon_code,
        "shipping_method": order.shipping_method,
        "shipping_service": order.shipping_service_json,
        "shipping_address": order.shipping_address_json,
        "customer_note": order.customer_note,
        "placed_at": order.placed_at,
        "events": [
            {
                "type": e.type,
                "from_status": e.from_status,
                "to_status": e.to_status,
                "message": e.message,
                "actor_type": e.actor_type,
                "created_at": e.created_at,
            }
            for e in sorted(order.events, key=lambda x: x.created_at or datetime.now(UTC))
        ],
    }


async def attach_variation_options(db: AsyncSession, out: dict) -> dict:
    """Enriquece cada item do pedido com as opções de Cor / Número cadastradas
    no produto correspondente — para os dropdowns da tela de edição."""
    from app.modules.products.models import VariantOptionType

    pids = {i["product_id"] for i in out.get("items", []) if i.get("product_id")}
    if not pids:
        return out
    rows = await db.scalars(
        select(VariantOptionType)
        .where(VariantOptionType.product_id.in_([uuid.UUID(p) for p in pids]))
        .options(selectinload(VariantOptionType.values))
    )
    cor_by_pid: dict[str, list[str]] = {}
    num_by_pid: dict[str, list[str]] = {}
    for ot in rows:
        pid = str(ot.product_id)
        vals = [v.value for v in sorted(ot.values, key=lambda x: x.position)]
        name = (ot.name or "").lower()
        if ot.is_color or "cor" in name:
            cor_by_pid.setdefault(pid, []).extend(vals)
        if ot.is_size or "num" in name or "tam" in name:
            num_by_pid.setdefault(pid, []).extend(vals)
    for item in out.get("items", []):
        pid = item.get("product_id")
        if not pid:
            continue
        item["cor_options"] = cor_by_pid.get(pid, [])
        item["numero_options"] = num_by_pid.get(pid, [])
    return out


def _customer_name(order: Order) -> str:
    """Nome do cliente para exibição: usa o destinatário do endereço; se não
    houver, cai para a parte local do e-mail e, por fim, o e-mail inteiro."""
    for src in (order.shipping_address_json, order.billing_address_json):
        if isinstance(src, dict):
            name = (src.get("recipient_name") or src.get("name") or "").strip()
            if name:
                return name
    if order.email and "@" in order.email:
        return order.email.split("@", 1)[0]
    return order.email or "—"


def list_item_out(order: Order) -> dict:
    items = list(order.items)
    total_qty = sum(i.quantity for i in items)
    if not items:
        summary = "—"
    elif len(items) == 1:
        summary = f"{items[0].name}"
        if items[0].quantity > 1:
            summary += f" (x{items[0].quantity})"
    else:
        summary = f"{items[0].name} + {len(items) - 1} item(ns)"
    return {
        "id": str(order.id),
        "number": order.number,
        "status": order.status,
        "payment_status": order.payment_status,
        "fulfillment_status": order.fulfillment_status,
        "email": order.email,
        "customer_name": _customer_name(order),
        "grand_total_cents": order.grand_total_cents,
        "placed_at": order.placed_at,
        "created_at": order.created_at,
        "items_summary": summary,
        "items_count": total_qty,
        "suppliers": sorted({i.supplier for i in items if i.supplier}),
    }


async def admin_list(
    db: AsyncSession,
    *,
    status: str | None = None,
    payment_status: str | None = None,
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> dict:
    from datetime import date

    stmt = select(Order).options(selectinload(Order.items))
    if status:
        stmt = stmt.where(Order.status == status)
    if payment_status:
        stmt = stmt.where(Order.payment_status == payment_status)
    if q:
        stmt = stmt.where((Order.number.ilike(f"%{q}%")) | (Order.email.ilike(f"%{q}%")))
    if date_from:
        try:
            stmt = stmt.where(Order.created_at >= datetime.combine(date.fromisoformat(date_from), datetime.min.time(), tzinfo=UTC))
        except ValueError:
            pass
    if date_to:
        try:
            stmt = stmt.where(Order.created_at <= datetime.combine(date.fromisoformat(date_to), datetime.max.time(), tzinfo=UTC))
        except ValueError:
            pass
    total = int(await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = await db.scalars(
        stmt.order_by(Order.placed_at.desc().nullslast(), Order.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    return {
        "items": [list_item_out(o) for o in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


_ADDR_KEYS = (
    "recipient_name", "zip", "street", "number", "complement",
    "district", "city", "state", "country", "phone",
)


async def edit_order(db: AsyncSession, number: str, data: dict) -> Order:
    """Edita dados do comprador/envio e rótulos dos itens (uso admin)."""
    order = await get_by_number(db, number)

    if data.get("email"):
        order.email = str(data["email"]).strip()
    if "cpf" in data:
        digits = "".join(ch for ch in str(data["cpf"] or "") if ch.isdigit())
        order.cpf = digits[:11] or None
    if data.get("customer_note") is not None:
        order.customer_note = str(data["customer_note"]).strip() or None
    if isinstance(data.get("shipping_address"), dict):
        addr = dict(order.shipping_address_json or {})
        for k in _ADDR_KEYS:
            if k in data["shipping_address"] and data["shipping_address"][k] is not None:
                val = str(data["shipping_address"][k]).strip()
                if k == "zip":
                    val = "".join(ch for ch in val if ch.isdigit())[:8]
                addr[k] = val
        order.shipping_address_json = addr
    if isinstance(data.get("shipping_service"), dict):
        svc = dict(order.shipping_service_json or {})
        svc.update({k: v for k, v in data["shipping_service"].items() if v is not None})
        order.shipping_service_json = svc
        if data["shipping_service"].get("tracking_code"):
            order.shipping_method = order.shipping_method  # noqa: keep

    for it_edit in data.get("items", []) or []:
        it = next((x for x in order.items if str(x.id) == str(it_edit.get("id"))), None)
        if not it:
            continue
        if it_edit.get("name"):
            it.name = str(it_edit["name"]).strip()
        # Variação estruturada (cor / número). Quando presente, recompõe o rótulo.
        has_struct = "cor" in it_edit or "numero" in it_edit
        if has_struct:
            attrs = dict(it.variant_attrs or {})
            if "cor" in it_edit:
                attrs["cor"] = (str(it_edit["cor"]).strip() or None) if it_edit["cor"] is not None else None
            if "numero" in it_edit:
                attrs["numero"] = (str(it_edit["numero"]).strip() or None) if it_edit["numero"] is not None else None
            attrs = {k: v for k, v in attrs.items() if v}
            it.variant_attrs = attrs or None
            it.variant_label = _variant_label_from_attrs(attrs.get("cor"), attrs.get("numero"))
        if it_edit.get("variant_label") is not None:
            it.variant_label = str(it_edit["variant_label"]).strip() or None

    await record_event(db, order, type="edited", actor_type="admin", message="Dados do pedido editados")
    await db.flush()
    return await _load(db, order.id)


async def delete_order(db: AsyncSession, number: str) -> None:
    """Apaga o pedido do banco (itens/eventos/pagamentos). Mantém o cliente."""
    from app.modules.payment.models import Payment, PaymentWebhookEvent

    order = await get_by_number(db, number)
    await db.execute(
        Payment.__table__.delete().where(Payment.order_id == order.id)
    )
    await db.execute(
        PaymentWebhookEvent.__table__.update()
        .where(PaymentWebhookEvent.order_id == order.id)
        .values(order_id=None)
    )
    await db.delete(order)  # items/events caem por cascade
    await db.flush()


async def admin_bulk(db: AsyncSession, numbers: list[str]) -> list[dict]:
    """Carrega vários pedidos completos (para PDF/etiquetas)."""
    rows = await db.scalars(
        select(Order)
        .where(Order.number.in_(numbers))
        .options(selectinload(Order.items), selectinload(Order.events))
        .order_by(Order.number)
    )
    return [to_out(o) for o in rows]
