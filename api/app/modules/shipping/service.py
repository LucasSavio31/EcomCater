"""Regra de negócio do módulo `shipping` — cotação com cache Redis + rastreio."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import DomainError, NotFoundError
from app.core.events import emit
from app.core.redis import redis_client
from app.modules.shipping.config import ShippingConfig
from app.modules.shipping.models import ShippingQuote
from app.modules.shipping.providers.base import Package, ShippingProvider, TrackingUpdate
from app.modules.shipping.providers.melhor_envio import MelhorEnvioProvider

logger = logging.getLogger("shipping.service")

_CACHE_PREFIX = "ship:quote:"
_PROVIDERS: dict[str, type[ShippingProvider]] = {"melhor_envio": MelhorEnvioProvider}


async def load_config(db: AsyncSession) -> ShippingConfig:
    from app.modules.admin.models import ModuleRow

    row = await db.get(ModuleRow, "shipping")
    raw = dict(row.config_json) if row and row.config_json else {}
    return ShippingConfig(**raw)


async def save_config(db: AsyncSession, patch: dict) -> ShippingConfig:
    from app.modules.admin.models import ModuleRow

    row = await db.get(ModuleRow, "shipping")
    current = dict(row.config_json) if row and row.config_json else {}
    for k, v in patch.items():
        if v is not None:
            current[k] = v
    cfg = ShippingConfig(**current)
    if row is None:
        row = ModuleRow(slug="shipping", enabled=True, config_json=cfg.model_dump())
        db.add(row)
    else:
        row.config_json = cfg.model_dump()
    row.updated_at = datetime.now(UTC)
    await db.flush()
    return cfg


def _provider(cfg: ShippingConfig) -> ShippingProvider:
    cls = _PROVIDERS.get(cfg.active_provider)
    if not cls:
        raise DomainError(f"Provedor de frete desconhecido: {cfg.active_provider}")
    if cfg.active_provider == "melhor_envio":
        base = (
            "https://sandbox.melhorenvio.com.br"
            if cfg.melhor_envio_sandbox
            else "https://melhorenvio.com.br"
        )
        return MelhorEnvioProvider(
            token=cfg.melhor_envio_token or settings.melhor_envio_token,
            base_url=base,
        )
    return cls()


def _cache_key(origin: str, dest: str, signature: str) -> str:
    h = hashlib.sha256(f"{origin}|{dest}|{signature}".encode()).hexdigest()[:24]
    return f"{_CACHE_PREFIX}{h}"


async def quote(
    db: AsyncSession,
    *,
    dest_zip: str,
    packages: list[Package],
    signature: str | None = None,
) -> list[dict]:
    cfg = await load_config(db)
    origin = cfg.origin_zip or settings.shipping_origin_zip
    sig = signature or hashlib.sha256(
        json.dumps([p.__dict__ for p in packages], sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    key = _cache_key(origin, dest_zip, sig)

    try:
        cached = await redis_client.get(key)
        if cached:
            return json.loads(cached)
    except Exception:  # noqa: BLE001
        pass

    provider = _provider(cfg)
    rates = await provider.quote(origin_zip=origin, dest_zip=dest_zip, packages=packages)
    payload = [r.as_dict() for r in rates]
    for r in payload:
        if r["id"] in cfg.free_shipping_services:
            r["price_cents"] = 0

    ttl = settings.shipping_quote_cache_ttl
    try:
        await redis_client.set(key, json.dumps(payload), ex=ttl)
    except Exception:  # noqa: BLE001
        pass

    db.add(
        ShippingQuote(
            cache_key=key.removeprefix(_CACHE_PREFIX),
            origin_zip=origin,
            dest_zip=dest_zip,
            packages_json=[p.__dict__ for p in packages],
            rates_json=payload,
            provider=cfg.active_provider,
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl),
        )
    )
    await db.flush()
    return payload


def _cart_packages(cart) -> list[Package]:
    pkgs: list[Package] = []
    for item in cart.items:
        pkgs.append(
            Package(
                weight_grams=300,
                length_mm=200,
                width_mm=150,
                height_mm=100,
                insurance_cents=item.unit_price_cents,
                quantity=item.quantity,
            )
        )
    return pkgs or [Package(300, 200, 150, 100)]


async def quote_for_cart(db: AsyncSession, cart) -> list[dict]:
    if not cart.shipping_zip:
        raise DomainError("Informe o CEP para calcular o frete.", code="missing_zip")
    from app.modules.cart.service import cart_items_signature

    return await quote(
        db,
        dest_zip=cart.shipping_zip,
        packages=_cart_packages(cart),
        signature=cart_items_signature(cart),
    )


async def get_cached_rate(
    db: AsyncSession, dest_zip: str, signature: str, service_id: str
) -> dict | None:
    cfg = await load_config(db)
    origin = cfg.origin_zip or settings.shipping_origin_zip
    key = _cache_key(origin, dest_zip, signature)
    try:
        cached = await redis_client.get(key)
        if cached:
            for r in json.loads(cached):
                if str(r["id"]) == str(service_id):
                    return r
    except Exception:  # noqa: BLE001
        pass
    return None


# --------------------------------------------------------------------- webhook / rastreio
async def handle_tracking_webhook(
    db: AsyncSession, headers: dict, raw_body: bytes, body: dict
) -> dict:
    cfg = await load_config(db)
    provider = _provider(cfg)
    if not provider.verify_webhook(headers, raw_body):
        raise DomainError("Assinatura de webhook inválida.", code="bad_signature")

    update: TrackingUpdate | None = provider.parse_webhook(headers, body)
    if not update:
        return {"ignored": True}

    from app.modules.orders.models import Order

    order = None
    if update.provider_shipment_id:
        order = await db.scalar(
            select(Order).where(
                Order.shipping_service_json["shipment_id"].astext == update.provider_shipment_id
            )
        )
    if not order and update.tracking_code:
        order = await db.scalar(
            select(Order).where(
                Order.shipping_service_json["tracking_code"].astext == update.tracking_code
            )
        )
    if not order:
        logger.info("webhook de rastreio sem pedido correspondente: %s", update)
        return {"matched": False}

    from app.modules.orders.service import record_event

    # 1) Persistir o código de rastreio assim que o Melhor Envio o informar.
    tracking_saved = False
    if update.tracking_code:
        svc = dict(order.shipping_service_json or {})
        if svc.get("tracking_code") != update.tracking_code:
            svc["tracking_code"] = update.tracking_code
            if update.provider_shipment_id:
                svc.setdefault("shipment_id", update.provider_shipment_id)
            order.shipping_service_json = svc
            tracking_saved = True
            await record_event(
                db, order, type="tracking_added", actor_type="system",
                message=f"Código de rastreio do Melhor Envio: {update.tracking_code}",
            )

    # 2) Mapear o status do rastreio para o status do pedido.
    #    EM_TRANSITO mantém 'shipped' mas dispara e-mail próprio ('in_transit').
    mapping = {
        "POSTADO": ("shipped", "shipped", "shipped"),
        "EM_TRANSITO": ("shipped", "shipped", "in_transit"),
        "ENTREGUE": ("delivered", "fulfilled", "delivered"),
    }
    new_status, new_fulfillment, email_key = mapping.get(
        update.status, (order.status, order.fulfillment_status, None)
    )
    status_changed = new_status != order.status
    if status_changed:
        prev = order.status
        order.status = new_status
        order.fulfillment_status = new_fulfillment
        await record_event(
            db, order, type="status_changed", from_status=prev, to_status=new_status,
            message=f"Rastreio Melhor Envio: {update.raw_status}", actor_type="system",
        )

    # Dispara o e-mail transacional adequado (inclusive quando só chegou o
    # rastreio, ou quando é EM_TRANSITO sem mudança de status do pedido).
    if email_key and (status_changed or email_key == "in_transit" or tracking_saved):
        await emit("order.status_changed", {"order_id": str(order.id), "status": email_key})

    return {"matched": True, "status": update.status, "tracking_saved": tracking_saved}


async def send_orders_to_melhor_envio(db: AsyncSession, order_numbers: list[str]) -> dict:
    """Adiciona cada pedido ao carrinho do Melhor Envio (`POST /api/v2/me/cart`).

    A compra/impressão da etiqueta é finalizada no painel do ME. Sem o token
    configurado (ou sem dados de remetente), devolve o motivo por pedido.
    """
    import httpx

    from app.modules.orders.models import Order

    cfg = await load_config(db)
    token = cfg.melhor_envio_token or settings.melhor_envio_token
    results: list[dict] = []
    if not token:
        for n in order_numbers:
            results.append({"number": n, "ok": False, "message": "Configure o token do Melhor Envio no menu Frete."})
        return {"results": results}

    base = (cfg.melhor_envio_api_url or settings.melhor_envio_api_url).rstrip("/") if hasattr(cfg, "melhor_envio_api_url") else settings.melhor_envio_api_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": settings.melhor_envio_user_agent,
    }
    origin = cfg.origin_zip or settings.shipping_origin_zip

    for number in order_numbers:
        order = await db.scalar(
            select(Order).where(Order.number == number).options(selectinload(Order.items))
        )
        if not order:
            results.append({"number": number, "ok": False, "message": "Pedido não encontrado."})
            continue
        addr = order.shipping_address_json or {}
        svc = (order.shipping_service_json or {})
        service_id = svc.get("id") or svc.get("service_id")
        if not service_id:
            results.append({"number": number, "ok": False, "message": "Pedido sem serviço de frete escolhido."})
            continue
        payload = {
            "service": int(service_id) if str(service_id).isdigit() else service_id,
            "from": {"postal_code": origin},
            "to": {
                "name": addr.get("recipient_name", ""),
                "phone": "".join(ch for ch in str(addr.get("phone", "")) if ch.isdigit()),
                "email": order.email,
                "address": addr.get("street", ""),
                "number": addr.get("number", ""),
                "complement": addr.get("complement", ""),
                "district": addr.get("district", ""),
                "city": addr.get("city", ""),
                "state_abbr": addr.get("state", ""),
                "country_id": "BR",
                "postal_code": "".join(ch for ch in str(addr.get("zip", "")) if ch.isdigit()),
            },
            "products": [
                {"name": it.name[:120], "quantity": it.quantity, "unitary_value": round(it.unit_price_cents / 100, 2)}
                for it in order.items
            ],
            "volumes": [{"height": 10, "width": 15, "length": 20, "weight": 0.5}],
            "options": {"insurance_value": round(order.grand_total_cents / 100, 2), "receipt": False, "own_hand": False},
        }
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post(f"{base}/api/v2/me/cart", headers=headers, json=payload)
            if r.status_code < 300:
                results.append({"number": number, "ok": True, "message": "Adicionado ao carrinho do Melhor Envio."})
            else:
                results.append({"number": number, "ok": False, "message": f"ME {r.status_code}: {r.text[:200]}"})
        except Exception as exc:  # noqa: BLE001
            results.append({"number": number, "ok": False, "message": f"Erro de rede: {exc}"})

    return {"results": results}
