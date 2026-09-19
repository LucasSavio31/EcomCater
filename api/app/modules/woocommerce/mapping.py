"""Conversão pro formato JSON da REST API do WooCommerce (schema oficial,
`https://woocommerce.github.io/woocommerce-rest-api-docs/`) -- funções
puras, sem I/O, pra ficarem fáceis de testar isoladas do banco."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.modules.orders.models import Order, OrderItem
from app.modules.products.models import Product, ProductVariant

# nosso status -> status do WooCommerce (vocabulário fixo deles: pending,
# processing, on-hold, completed, cancelled, refunded, failed, trash).
ORDER_STATUS_TO_WC: dict[str, str] = {
    "pending_payment": "pending",
    "paid": "processing",
    "processing": "processing",
    "tracking_available": "processing",
    "shipped": "completed",
    "delivered": "completed",
    "canceled": "cancelled",
    "refunded": "refunded",
    "returned": "refunded",
    "returning": "processing",
    "return_completed": "refunded",
}

# status do WooCommerce -> nosso status, quando o ERP escreve de volta
# (`PUT /wp-json/wc/v3/orders/<id>`). "completed" vira "shipped" (não
# "delivered" -- não dá pra presumir confirmação de entrega só pelo ERP
# marcar como concluído).
WC_STATUS_TO_ORDER: dict[str, str] = {
    "pending": "pending_payment",
    "on-hold": "processing",
    "processing": "processing",
    "completed": "shipped",
    "cancelled": "canceled",
    "refunded": "refunded",
    "failed": "pending_payment",
}


def _money(cents: int) -> str:
    return f"{cents / 100:.2f}"


def _iso(dt: datetime | None) -> str:
    return (dt or datetime.now()).replace(microsecond=0).isoformat()


def _address_from_shipping(addr: dict, *, email: str | None = None, phone: str | None = None) -> dict:
    parts = (addr.get("recipient_name") or "").split(" ", 1)
    first, last = (parts[0], parts[1]) if len(parts) > 1 else (parts[0] if parts else "", "")
    out = {
        "first_name": first,
        "last_name": last,
        "company": "",
        "address_1": f"{addr.get('street', '')}, {addr.get('number', '')}".strip(", "),
        "address_2": addr.get("complement") or "",
        "city": addr.get("city") or "",
        "state": addr.get("state") or "",
        "postcode": (addr.get("zip") or "").replace("-", ""),
        "country": "BR",
    }
    if email is not None:
        out["email"] = email
    if phone is not None:
        out["phone"] = phone or ""
    return out


def order_line_items(items: list[OrderItem], *, product_wc_ids: dict[str, int]) -> list[dict]:
    out = []
    for it in items:
        out.append(
            {
                "id": 0,
                "name": it.name + (f" - {it.variant_label}" if it.variant_label else ""),
                "product_id": product_wc_ids.get(str(it.product_id)) or 0,
                "variation_id": 0,
                "quantity": it.quantity,
                "sku": it.sku,
                "price": it.unit_price_cents / 100,
                "subtotal": _money(it.unit_price_cents * it.quantity),
                "total": _money(it.total_cents),
                "meta_data": (
                    [{"key": k, "value": v} for k, v in (it.variant_attrs or {}).items()]
                    if it.variant_attrs
                    else []
                ),
            }
        )
    return out


def order_to_wc(order: Order, *, product_wc_ids: dict[str, int] | None = None) -> dict[str, Any]:
    addr = order.shipping_address_json or {}
    billing = _address_from_shipping(addr, email=order.email, phone=addr.get("phone"))
    shipping = _address_from_shipping(addr)
    meta_data = []
    if order.cpf:
        meta_data.append({"key": "_billing_persontype", "value": "1"})
        meta_data.append({"key": "_billing_cpf", "value": order.cpf})
    svc = order.shipping_service_json or {}
    if svc.get("tracking_code"):
        meta_data.append({"key": "_tracking_number", "value": svc["tracking_code"]})
        if svc.get("tracking_url"):
            meta_data.append({"key": "_tracking_url", "value": svc["tracking_url"]})
    return {
        "id": order.wc_id,
        "parent_id": 0,
        "number": order.number,
        "order_key": f"order_{order.id}",
        "created_via": "checkout",
        "status": ORDER_STATUS_TO_WC.get(order.status, "pending"),
        "currency": order.currency,
        "date_created": _iso(order.placed_at or order.created_at),
        "date_modified": _iso(order.updated_at),
        "discount_total": _money(order.discount_cents),
        "shipping_total": _money(order.shipping_cents),
        "total": _money(order.grand_total_cents),
        "total_tax": "0.00",
        "customer_id": 0,
        "customer_note": order.customer_note or "",
        "billing": billing,
        "shipping": shipping,
        "payment_method": (order.shipping_method or ""),
        "payment_method_title": order.shipping_method or "",
        "line_items": order_line_items(order.items, product_wc_ids=product_wc_ids or {}),
        "shipping_lines": (
            [
                {
                    "id": 0,
                    "method_title": order.shipping_method or "Frete",
                    "method_id": "flat_rate",
                    "total": _money(order.shipping_cents),
                }
            ]
            if order.shipping_cents
            else []
        ),
        "meta_data": meta_data,
    }


def variation_to_wc(
    product: Product, variant: ProductVariant, *, image_url: str | None, attrs: dict[str, str]
) -> dict[str, Any]:
    price_cents = variant.price_cents if variant.price_cents is not None else product.price_cents
    return {
        "id": variant.wc_id,
        "sku": variant.sku,
        "price": _money(price_cents),
        "regular_price": _money(price_cents),
        "sale_price": "",
        "stock_quantity": variant.stock_qty,
        "manage_stock": variant.stock_qty is not None,
        "in_stock": bool(variant.is_active and (variant.stock_qty is None or variant.stock_qty > 0)),
        "status": "publish" if variant.is_active else "private",
        "weight": str((variant.weight_grams or product.weight_grams) / 1000),
        "image": ({"src": image_url} if image_url else None),
        "attributes": [{"name": k, "option": v} for k, v in attrs.items()],
    }


def product_to_wc(
    product: Product,
    *,
    variants: list[ProductVariant],
    primary_image_url: str | None,
    category_name: str | None,
    variation_ids: list[int],
) -> dict[str, Any]:
    total_stock = None
    if variants:
        known = [v.stock_qty for v in variants if v.stock_qty is not None]
        total_stock = sum(known) if known else None
    in_stock = any(
        v.is_active and (v.stock_qty is None or v.stock_qty > 0) for v in variants
    ) if variants else True
    return {
        "id": product.wc_id,
        "name": product.name,
        "slug": product.slug,
        "type": "variable" if variants else "simple",
        "status": "publish" if product.status == "active" else "draft",
        "sku": product.sku_root or "",
        "price": _money(product.price_cents),
        "regular_price": _money(product.compare_at_price_cents or product.price_cents),
        "sale_price": _money(product.price_cents) if product.compare_at_price_cents else "",
        "description": product.description or "",
        "short_description": product.short_description or "",
        "stock_quantity": total_stock,
        "manage_stock": total_stock is not None,
        "in_stock": in_stock,
        "categories": ([{"id": 0, "name": category_name}] if category_name else []),
        "images": ([{"src": primary_image_url}] if primary_image_url else []),
        "variations": variation_ids,
        "date_created": _iso(product.created_at),
        "date_modified": _iso(product.updated_at),
    }
