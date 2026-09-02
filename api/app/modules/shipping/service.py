"""Regra de negócio do módulo `shipping` — cotação com cache Redis + rastreio."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import logging
import secrets
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
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

def _service_allowed(rate: dict, allowed: set[str]) -> bool:
    """A tarifa passa se o serviço (ou sua 1ª palavra) estiver na lista permitida."""
    name = str(rate.get("service", "")).strip().lower()
    if not name:
        return False
    return name in allowed or name.split(" ", 1)[0] in allowed


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


def _me_base(cfg: ShippingConfig) -> str:
    return (
        "https://sandbox.melhorenvio.com.br"
        if cfg.melhor_envio_sandbox
        else "https://melhorenvio.com.br"
    )


def _provider(cfg: ShippingConfig) -> ShippingProvider:
    cls = _PROVIDERS.get(cfg.active_provider)
    if not cls:
        raise DomainError(f"Provedor de frete desconhecido: {cfg.active_provider}")
    if cfg.active_provider == "melhor_envio":
        return MelhorEnvioProvider(
            token=cfg.melhor_envio_token or settings.melhor_envio_token,
            base_url=_me_base(cfg),
        )
    return cls()


# --------------------------------------------------------------------- OAuth Melhor Envio
_ME_OAUTH_SCOPES = (
    "shipping-calculate cart-read cart-write shipping-generate shipping-preview "
    "shipping-checkout shipping-print shipping-tracking shipping-cancel orders-read"
)


def melhor_envio_redirect_uri() -> str:
    return f"{settings.public_api_url.rstrip('/')}/api/shipping/melhor-envio/callback"


async def melhor_envio_authorize_url(db: AsyncSession) -> str:
    """Gera o `state` (CSRF), grava-o e devolve a URL de autorização do ME."""
    cfg = await load_config(db)
    if not cfg.melhor_envio_client_id or not cfg.melhor_envio_client_secret:
        raise DomainError(
            "Informe o Client ID e o Client Secret do app Melhor Envio antes de conectar.",
            code="me_oauth_missing_app",
        )
    state = secrets.token_urlsafe(24)
    await save_config(
        db,
        {
            "melhor_envio_oauth_state": state,
            "melhor_envio_oauth_state_at": datetime.now(UTC).isoformat(),
        },
    )
    query = urlencode(
        {
            "client_id": cfg.melhor_envio_client_id,
            "redirect_uri": melhor_envio_redirect_uri(),
            "response_type": "code",
            "state": state,
            "scope": _ME_OAUTH_SCOPES,
        }
    )
    return f"{_me_base(cfg)}/oauth/authorize?{query}"


async def melhor_envio_exchange_code(db: AsyncSession, *, code: str, state: str) -> None:
    """Troca o `code` do callback por access/refresh token e salva na config."""
    cfg = await load_config(db)
    saved_state = cfg.melhor_envio_oauth_state
    saved_at = cfg.melhor_envio_oauth_state_at
    fresh = False
    if saved_at:
        try:
            fresh = datetime.now(UTC) - datetime.fromisoformat(saved_at) < timedelta(minutes=15)
        except ValueError:
            fresh = False
    if not saved_state or not secrets.compare_digest(saved_state, state or "") or not fresh:
        raise DomainError("Sessão de conexão expirada. Tente conectar novamente.", code="me_oauth_bad_state")

    payload = {
        "grant_type": "authorization_code",
        "client_id": cfg.melhor_envio_client_id,
        "client_secret": cfg.melhor_envio_client_secret,
        "redirect_uri": melhor_envio_redirect_uri(),
        "code": code,
    }
    tokens = await _me_token_request(cfg, payload)
    await _store_me_tokens(db, tokens)
    # limpa o state usado
    await save_config(db, {"melhor_envio_oauth_state": "", "melhor_envio_oauth_state_at": ""})


async def _me_token_request(cfg: ShippingConfig, payload: dict) -> dict:
    url = f"{_me_base(cfg)}/oauth/token"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": settings.melhor_envio_user_agent,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.warning("Melhor Envio OAuth falhou: %s %s", exc.response.status_code, exc.response.text[:300])
        raise DomainError(
            "Melhor Envio recusou a conexão (verifique Client ID/Secret e a Redirect URI cadastrada no app).",
            code="me_oauth_failed",
        ) from exc
    except httpx.HTTPError as exc:
        raise DomainError("Não foi possível falar com o Melhor Envio agora.", code="me_oauth_unavailable") from exc
    if not data.get("access_token"):
        raise DomainError("Resposta do Melhor Envio sem access_token.", code="me_oauth_failed")
    return data


async def _store_me_tokens(db: AsyncSession, tokens: dict) -> None:
    expires_in = int(tokens.get("expires_in") or 0)
    expires_at = (
        (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat() if expires_in else ""
    )
    patch = {
        "melhor_envio_token": tokens["access_token"],
        "melhor_envio_token_expires_at": expires_at,
    }
    if tokens.get("refresh_token"):
        patch["melhor_envio_refresh_token"] = tokens["refresh_token"]
    await save_config(db, patch)


async def _maybe_refresh_me_token(db: AsyncSession, cfg: ShippingConfig) -> ShippingConfig:
    """Renova o access_token se estiver a <2 dias de expirar (ou já expirado)."""
    if cfg.active_provider != "melhor_envio" or not cfg.melhor_envio_refresh_token:
        return cfg
    exp = cfg.melhor_envio_token_expires_at
    if exp:
        try:
            if datetime.fromisoformat(exp) - datetime.now(UTC) > timedelta(days=2):
                return cfg
        except ValueError:
            pass
    try:
        tokens = await _me_token_request(
            cfg,
            {
                "grant_type": "refresh_token",
                "client_id": cfg.melhor_envio_client_id,
                "client_secret": cfg.melhor_envio_client_secret,
                "refresh_token": cfg.melhor_envio_refresh_token,
            },
        )
    except DomainError:
        logger.warning("Melhor Envio: refresh do token falhou; seguindo com o token atual.")
        return cfg
    await _store_me_tokens(db, tokens)
    return await load_config(db)


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
    cfg = await _maybe_refresh_me_token(db, cfg)
    origin = cfg.origin_zip or settings.shipping_origin_zip
    sig = signature or hashlib.sha256(
        json.dumps([asdict(p) for p in packages], sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    key = _cache_key(origin, dest_zip, sig)

    allowed = {s.strip().lower() for s in (cfg.allowed_services or []) if s.strip()}

    try:
        cached = await redis_client.get(key)
        if cached:
            return [d for d in json.loads(cached) if _service_allowed(d, allowed)]
    except Exception:  # noqa: BLE001
        pass

    provider = _provider(cfg)
    rates = await provider.quote(origin_zip=origin, dest_zip=dest_zip, packages=packages)
    # Aplica a regra de serviços permitidos (PAC/SEDEX por padrão).
    payload = [d for d in (r.as_dict() for r in rates) if _service_allowed(d, allowed)]
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
            packages_json=[asdict(p) for p in packages],
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


FREE_SHIPPING_OPTION = {
    "id": "free",
    "service": "Frete grátis",
    "carrier": "Loja",
    "price_cents": 0,
    "delivery_days": 0,
}


async def free_shipping_min_cents(db: AsyncSession) -> int | None:
    """Valor de subtotal a partir do qual o frete é grátis (configurado na
    página Frete). None/0 = desligado."""
    cfg = await load_config(db)
    v = getattr(cfg, "free_shipping_min_cents", None)
    return int(v) if v else None


async def quote_for_cart(db: AsyncSession, cart) -> list[dict]:
    cfg = await load_config(db)
    if getattr(cfg, "free_shipping_all", False):
        return [dict(FREE_SHIPPING_OPTION)]

    # frete grátis automático ao atingir o valor mínimo do pedido
    min_cents = await free_shipping_min_cents(db)
    if min_cents:
        subtotal = sum(i.unit_price_cents * i.quantity for i in cart.items)
        if subtotal >= min_cents:
            return [dict(FREE_SHIPPING_OPTION)]

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


# --------------------------------------------------------------------- Etiqueta Melhor Envio
def _digits(v: object) -> str:
    return "".join(ch for ch in str(v or "") if ch.isdigit())


def _me_err(step: str, r: httpx.Response) -> str:
    msg = None
    try:
        j = r.json()
        msg = j.get("message") or j.get("error")
        if not msg and isinstance(j.get("errors"), dict):
            msg = "; ".join(
                str(v[0] if isinstance(v, list) else v) for v in j["errors"].values()
            )
    except Exception:  # noqa: BLE001
        pass
    return f"Melhor Envio ({step}) {r.status_code}: {msg or r.text[:200]}"


_NO_BALANCE_HINTS = (
    "saldo insuficiente",
    "saldo é insuficiente",
    "saldo e insuficiente",
    "sem saldo",
    "não possui saldo",
    "nao possui saldo",
    "adicione saldo",
    "insufficient balance",
    "insufficient funds",
    "balance is insufficient",
    "not enough balance",
)


def _me_is_no_balance(r: httpx.Response) -> bool:
    """A compra falhou por falta de saldo na carteira do Melhor Envio?"""
    blob = (r.text or "").lower()
    try:
        data = r.json()
        blob += " " + (data if isinstance(data, str) else json.dumps(data)).lower()
    except Exception:  # noqa: BLE001
        pass
    return any(h in blob for h in _NO_BALANCE_HINTS)


def _me_pick_order(checkout: dict, shipment_id: str) -> dict:
    purchase = (checkout or {}).get("purchase") or checkout or {}
    orders = purchase.get("orders") or []
    for o in orders:
        if str(o.get("id")) == str(shipment_id):
            return o
    return orders[0] if orders else {}


def _svc_public(svc: dict) -> dict:
    return {
        "shipment_id": svc.get("shipment_id"),
        "protocol": svc.get("protocol"),
        "tracking_code": svc.get("tracking_code"),
        "label_url": svc.get("label_url"),
        "me_status": svc.get("me_status"),
    }


async def _me_from_block(db: AsyncSession, cfg: ShippingConfig, origin: str) -> dict:
    """Remetente da etiqueta = dados da loja (Aparência → Dados da loja) + CPF do
    responsável (menu Frete)."""
    from app.modules.admin.models import StoreSettings

    st = (await db.scalars(select(StoreSettings))).first()
    sa = (st.address_json if st and st.address_json else {}) or {}
    cpf = _digits(cfg.sender_cpf)
    cnpj = _digits((st.cnpj if st else "") or "")
    return {
        "name": (st.legal_name or st.store_name if st else None) or "Loja",
        "phone": _digits((st.contact_phone or st.contact_whatsapp if st else "") or ""),
        "email": settings.smtp_from_email,
        "document": cpf,
        "company_document": (cnpj if len(cnpj) == 14 else None),
        "address": sa.get("street", ""),
        "number": str(sa.get("number", "")),
        "complement": sa.get("complement") or "",
        "district": sa.get("district", ""),
        "city": sa.get("city", ""),
        "state_abbr": (sa.get("state") or "").upper()[:2],
        "country_id": "BR",
        "postal_code": _digits(sa.get("zip") or origin),
    }


# regra do lojista (status do pedido conforme o Melhor Envio):
#  - etiqueta enviada ao ME, ainda sem rastreio  -> "em separação" (processing)
#  - ME emitiu a etiqueta / devolveu o rastreio   -> "rastreio disponível" (tracking_available)
#  - ME marcou como postado nos Correios          -> "enviado" (shipped)
#  - ME marcou como entregue                      -> "entregue" (delivered)
_ORDER_STATUS_RANK = {
    "pending_payment": 0, "paid": 1, "processing": 2,
    "tracking_available": 3, "shipped": 4, "delivered": 5,
}


async def _me_apply_tracking(
    db: AsyncSession,
    order,
    *,
    tracking_code: str | None,
    me_status: str | None,
    source: str = "etiqueta",
) -> bool:
    """Registra o código de rastreio e avança o status do pedido conforme o
    Melhor Envio. Nunca retrocede status nem mexe em pedido cancelado/estornado.
    Devolve True se algo mudou."""
    from app.modules.orders.service import record_event

    changed = False
    svc = dict(order.shipping_service_json or {})

    if tracking_code and svc.get("tracking_code") != tracking_code:
        svc["tracking_code"] = tracking_code
        order.shipping_service_json = svc
        changed = True
        await record_event(
            db, order, type="tracking_added", actor_type="system",
            message=f"Código de rastreio do Melhor Envio: {tracking_code}",
        )

    me_norm = (me_status or "").lower()
    prev_me = (svc.get("me_tracking_status") or "").lower()
    if me_status and prev_me != me_norm:
        svc["me_tracking_status"] = me_status
        order.shipping_service_json = svc
        changed = True
        # "postado" e "entregue" chegam pela API (rotina/webhook). Quando o pedido
        # já está "enviado", registra o marco no histórico e dispara o e-mail.
        if me_norm == "posted" and order.status == "shipped":
            await record_event(
                db, order, type="tracking_update", actor_type="system",
                message="Melhor Envio: objeto postado nos Correios.",
            )
            await emit("order.status_changed", {"order_id": str(order.id), "status": "in_transit"})

    # envio cancelado/expirado no ME não mexe no status do pedido da loja
    if me_norm in {"canceled", "cancelled", "expired"}:
        return changed

    # só avança o status de pedido já pago (nunca de um pedido não pago)
    if order.status not in {"paid", "processing", "tracking_available", "shipped"}:
        return changed

    has_tracking = bool(tracking_code or svc.get("tracking_code"))
    if me_norm == "delivered":
        target = "delivered"
    elif me_norm in {"posted", "in_transit"}:
        target = "shipped"                       # postado nos Correios -> enviado
    elif has_tracking:
        target = "tracking_available"            # etiqueta emitida / rastreio recebido
    elif svc.get("shipment_id"):
        target = "processing"                    # etiqueta no ME, sem rastreio -> em separação
    else:
        target = None
    if target and _ORDER_STATUS_RANK.get(target, 0) > _ORDER_STATUS_RANK.get(order.status, 0):
        prev = order.status
        order.status = target
        if target == "delivered":
            order.fulfillment_status = "fulfilled"
        elif order.fulfillment_status in {"unfulfilled", ""}:
            order.fulfillment_status = "partial"
        _labels = {
            "processing": "em separação", "tracking_available": "rastreio disponível",
            "shipped": "enviado", "delivered": "entregue",
        }
        await record_event(
            db, order, type="status_changed", from_status=prev, to_status=target,
            message=f"Melhor Envio ({source}): pedido marcado como {_labels.get(target, target)}.",
            actor_type="system",
        )
        await emit("order.status_changed", {"order_id": str(order.id), "status": target})
        changed = True
    return changed


async def _me_label_for_order(
    c: httpx.AsyncClient,
    base: str,
    db: AsyncSession,
    number: str,
    from_block: dict,
    pkg,
    *,
    buy: bool,
) -> dict:
    from sqlalchemy.orm import selectinload

    from app.modules.orders.models import Order

    order = await db.scalar(
        select(Order).where(Order.number == number).options(selectinload(Order.items))
    )
    if not order:
        return {"number": number, "ok": False, "message": "Pedido não encontrado."}

    svc = dict(order.shipping_service_json or {})
    if svc.get("label_url"):
        return {"number": number, "ok": True, "message": "Etiqueta já gerada.", **_svc_public(svc)}

    service_id = svc.get("id") or svc.get("service_id")
    if not service_id or str(service_id) in {"free", "0"}:
        return {"number": number, "ok": False, "message": "Pedido sem serviço dos Correios (PAC/SEDEX)."}

    addr = order.shipping_address_json or {}
    _req = ("street", "number", "district", "city", "state", "zip")
    _missing = [k for k in _req if not str(addr.get(k) or "").strip()]
    if _missing:
        return {
            "number": number,
            "ok": False,
            "message": f"Endereço de entrega do pedido incompleto (falta: {', '.join(_missing)}).",
        }
    total_qty = sum(it.quantity for it in order.items) or 1
    reminder = f"Pedido {number}"
    shipment_id = svc.get("shipment_id")

    # 1) adiciona ao carrinho do Melhor Envio
    if not shipment_id:
        payload = {
            "service": int(service_id) if str(service_id).isdigit() else service_id,
            "from": from_block,
            "to": {
                "name": addr.get("recipient_name") or order.email,
                "phone": _digits(addr.get("phone", "")),
                "email": order.email,
                "document": _digits(order.cpf or addr.get("cpf") or ""),
                "address": addr.get("street", ""),
                "number": str(addr.get("number", "")),
                "complement": addr.get("complement") or "",
                "district": addr.get("district", ""),
                "city": addr.get("city", ""),
                "state_abbr": (addr.get("state") or "").upper()[:2],
                "country_id": "BR",
                "postal_code": _digits(addr.get("zip", "")),
            },
            "products": [
                {
                    "name": (it.name or "Item")[:120],
                    "quantity": it.quantity,
                    "unitary_value": round(it.unit_price_cents / 100, 2),
                }
                for it in order.items
            ],
            "volumes": [
                {
                    "height": max(1, round((getattr(pkg, "height_mm", 100) or 100) / 10)),
                    "width": max(1, round((getattr(pkg, "width_mm", 150) or 150) / 10)),
                    "length": max(1, round((getattr(pkg, "length_mm", 200) or 200) / 10)),
                    "weight": round(
                        max(1, (getattr(pkg, "weight_grams", 300) or 300)) * total_qty / 1000, 3
                    ),
                }
            ],
            "options": {
                "insurance_value": round(order.grand_total_cents / 100, 2),
                "receipt": False,
                "own_hand": False,
                "reminder": reminder,
                "platform": "Loja",
                "tags": [{"tag": reminder, "url": None}],
            },
        }
        r = await c.post(f"{base}/api/v2/me/cart", json=payload)
        if r.status_code >= 300:
            return {"number": number, "ok": False, "message": _me_err("carrinho", r)}
        shipment_id = str((r.json() or {}).get("id") or "")
        if not shipment_id:
            return {"number": number, "ok": False, "message": "Melhor Envio não retornou o id do envio."}
        svc.update({"shipment_id": shipment_id, "me_status": "cart", "me_reminder": reminder})
        order.shipping_service_json = dict(svc)

    # etiqueta já foi enviada ao Melhor Envio -> pedido entra "em separação"
    await _me_apply_tracking(
        db, order, tracking_code=None, me_status=None, source="etiqueta enviada"
    )

    if not buy:
        return {
            "number": number,
            "ok": True,
            "message": "Adicionado ao carrinho do Melhor Envio.",
            **_svc_public(svc),
        }

    # 2) compra (debita o saldo da conta)
    r = await c.post(f"{base}/api/v2/me/shipment/checkout", json={"orders": [shipment_id]})
    checkout: dict = {}
    try:
        checkout = r.json()
    except Exception:  # noqa: BLE001
        pass
    _already = any(w in r.text.lower() for w in ("already", "paid", "generated"))
    if r.status_code >= 300 and not _already:
        # Sem saldo na carteira do Melhor Envio: o envio JÁ está no carrinho do ME
        # (passo 1 feito). Não trata como erro — o lojista paga no painel do
        # Melhor Envio e a etiqueta/rastreio entram depois (rotina de sync ou
        # reenvio). O pedido já ficou "em separação" acima.
        if _me_is_no_balance(r):
            svc["me_status"] = "awaiting_me_payment"
            order.shipping_service_json = dict(svc)
            return {
                "number": number,
                "ok": True,
                "message": (
                    "Sem saldo no Melhor Envio — o envio foi criado no carrinho do ME. "
                    "Faça o pagamento no painel do Melhor Envio; a etiqueta e o rastreio "
                    "são sincronizados automaticamente depois."
                ),
                **_svc_public(svc),
            }
        return {"number": number, "ok": False, "message": _me_err("compra", r)}

    po = _me_pick_order(checkout, shipment_id)
    protocol = ((checkout.get("purchase") or {}).get("protocol")) or po.get("protocol") or svc.get("protocol")
    tracking = po.get("tracking") or po.get("self_tracking") or svc.get("tracking_code")
    if protocol:
        svc["protocol"] = protocol
    if tracking:
        svc["tracking_code"] = tracking
    svc["me_status"] = "purchased"
    order.shipping_service_json = dict(svc)

    # 3) gera a etiqueta
    r = await c.post(f"{base}/api/v2/me/shipment/generate", json={"orders": [shipment_id]})
    try:
        gen = r.json() if r.status_code < 300 else {}
    except Exception:  # noqa: BLE001
        gen = {}
    g = gen.get(shipment_id) if isinstance(gen, dict) else None
    if isinstance(g, dict) and g.get("tracking"):
        svc["tracking_code"] = g["tracking"]

    # 4) imprime — link público do PDF
    r = await c.post(f"{base}/api/v2/me/shipment/print", json={"mode": "public", "orders": [shipment_id]})
    label_url = None
    if r.status_code < 300:
        try:
            label_url = (r.json() or {}).get("url")
        except Exception:  # noqa: BLE001
            pass

    # 5) tenta pegar o código de rastreio (pode não sair na hora)
    if not svc.get("tracking_code"):
        r = await c.post(f"{base}/api/v2/me/shipment/tracking", json={"orders": [shipment_id]})
        if r.status_code < 300:
            try:
                t = (r.json() or {}).get(shipment_id) or {}
                code = t.get("tracking") or t.get("melhorenvio_tracking")
                if code:
                    svc["tracking_code"] = code
            except Exception:  # noqa: BLE001
                pass
    if label_url:
        svc["label_url"] = label_url
        svc["me_status"] = "label_ready"
    order.shipping_service_json = dict(svc)
    if order.fulfillment_status in {"unfulfilled", ""}:
        order.fulfillment_status = "partial"

    ok = bool(label_url)
    if ok:
        await _me_apply_tracking(
            db, order, tracking_code=svc.get("tracking_code"),
            me_status=svc.get("me_tracking_status"), source="etiqueta gerada",
        )
    return {
        "number": number,
        "ok": ok,
        "message": (
            "Etiqueta comprada e gerada."
            if ok
            else "Compra registrada, mas o PDF ainda não saiu. Rode 'Comprar e gerar etiqueta' de novo em alguns segundos."
        ),
        **_svc_public(svc),
    }


async def melhor_envio_print_url(db: AsyncSession, order_numbers: list[str]) -> str:
    """Devolve a URL pública de impressão do Melhor Envio para os pedidos
    informados (o ME não expõe o PDF por API — só a página de impressão)."""
    from sqlalchemy.orm import selectinload

    from app.modules.orders.models import Order

    cfg = await load_config(db)
    cfg = await _maybe_refresh_me_token(db, cfg)
    token = cfg.melhor_envio_token or settings.melhor_envio_token
    if not token:
        raise DomainError("Configure o token do Melhor Envio no menu Frete.", code="me_no_token")

    rows = await db.scalars(
        select(Order).where(Order.number.in_(order_numbers)).options(selectinload(Order.items))
    )
    ids = [
        (o.shipping_service_json or {}).get("shipment_id")
        for o in rows
        if (o.shipping_service_json or {}).get("shipment_id")
    ]
    ids = [i for i in ids if i]
    if not ids:
        raise DomainError("Nenhum dos pedidos tem etiqueta gerada no Melhor Envio.", code="me_no_labels")

    base = _me_base(cfg)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": settings.melhor_envio_user_agent,
    }
    async with httpx.AsyncClient(timeout=40, headers=headers, follow_redirects=True) as c:
        # garante que estão gerados e devolve a URL pública de impressão do ME
        await c.post(f"{base}/api/v2/me/shipment/generate", json={"orders": ids})
        r = await c.post(
            f"{base}/api/v2/me/shipment/print", json={"mode": "public", "orders": ids}
        )
    if r.status_code >= 300:
        raise DomainError(_me_err("impressão", r), code="me_print_failed")
    url = (r.json() or {}).get("url")
    if not url:
        raise DomainError("Melhor Envio não retornou a etiqueta.", code="me_print_empty")
    return url


async def _me_set_checkbox(page, selector: str, value: bool) -> None:
    try:
        if await page.is_checked(selector) != value:
            await page.set_checked(selector, value, force=True)
    except Exception:  # noqa: BLE001 - controle pode não existir p/ este envio
        logger.debug("checkbox %s não encontrado na página de impressão do ME", selector)


async def _render_url_to_pdf(url: str, *, postal_card: bool, want_declaration: bool) -> bytes:
    """Abre a página pública de impressão do Melhor Envio num navegador headless,
    ajusta as opções (tamanho 10x15, DACE simples) e devolve o PDF renderizado
    (a etiqueta é desenhada em <canvas> no cliente)."""
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:  # pragma: no cover - dependência opcional
        raise DomainError(
            "Geração de PDF de etiqueta indisponível: instale o playwright no servidor "
            "(pip install playwright && playwright install chromium).",
            code="me_pdf_no_playwright",
        ) from exc

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox"])
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=60_000)
            await page.wait_for_timeout(3500)

            body = (await page.inner_text("body")).lower()
            if "destinat" not in body and "recebedor" not in body and "remetente" not in body:
                raise DomainError(
                    "O Melhor Envio não renderizou a etiqueta (a etiqueta pode ainda "
                    "estar sendo gerada — tente de novo em alguns segundos).",
                    code="me_pdf_empty",
                )

            # opções da página de impressão do ME
            await _me_set_checkbox(page, "#postal_card", postal_card)        # 10x15
            await _me_set_checkbox(page, "#print_tags", True)               # etiqueta
            await _me_set_checkbox(page, "#print_daces", want_declaration)  # DACE simples
            await _me_set_checkbox(page, "#print_complete_daces", False)    # nunca a completa
            await _me_set_checkbox(page, "#print_packing_lists", False)     # sem romaneio
            for name in ("IMPRIMIR", "Visualizar Etiquetas", "Visualizar"):
                btn = page.get_by_role("button", name=name)
                if await btn.count():
                    with contextlib.suppress(Exception):
                        await btn.first.click(timeout=4000)
                    break
            await page.wait_for_timeout(5000)

            if postal_card:
                return await page.pdf(prefer_css_page_size=True, print_background=True)
            return await page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "6mm", "bottom": "6mm", "left": "6mm", "right": "6mm"},
            )
        finally:
            await browser.close()


def _labels_a4_4up(pdf: bytes) -> bytes:
    """Reagrupa as páginas em folhas A4 com 4 etiquetas por página."""
    try:
        from pypdf import PdfReader, PdfWriter, Transformation

        reader = PdfReader(io.BytesIO(pdf))
        pages = list(reader.pages)
        if len(pages) <= 1:
            return pdf
        a4_w, a4_h = 595.32, 841.92  # pt, retrato
        cell_w, cell_h = a4_w / 2, a4_h / 2
        writer = PdfWriter()
        for i in range(0, len(pages), 4):
            sheet = writer.add_blank_page(width=a4_w, height=a4_h)
            for j, src in enumerate(pages[i : i + 4]):
                sw = float(src.mediabox.width) or cell_w
                sh = float(src.mediabox.height) or cell_h
                scale = min(cell_w / sw, cell_h / sh)
                col, row = j % 2, j // 2
                tx = col * cell_w
                ty = a4_h - (row + 1) * cell_h
                sheet.merge_transformed_page(
                    src, Transformation().scale(scale).translate(tx, ty)
                )
        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao montar as etiquetas em A4 4-up")
        return pdf


async def melhor_envio_labels_pdf(db: AsyncSession, order_numbers: list[str]) -> bytes:
    """PDF das etiquetas dos pedidos, pronto para baixar no painel da loja
    (sem abrir o site do Melhor Envio). Respeita o formato e a opção de
    Declaração de Conteúdo definidos no menu Frete."""
    url = await melhor_envio_print_url(db, order_numbers)
    cfg = await load_config(db)
    fmt = cfg.label_format or "termica_10x15"
    pdf = await _render_url_to_pdf(
        url,
        postal_card=(fmt != "a4_4up"),
        want_declaration=bool(cfg.print_declaration),
    )
    if fmt == "a4_4up":
        pdf = _labels_a4_4up(pdf)
    return pdf


async def send_orders_to_melhor_envio(
    db: AsyncSession, order_numbers: list[str], *, buy: bool = True
) -> dict:
    """Fluxo completo da etiqueta: carrinho -> compra (saldo) -> gerar -> imprimir (PDF).

    Salva no pedido o id do envio, protocolo, código de rastreio e o link do PDF.
    `buy=False` para no carrinho (finaliza no painel do Melhor Envio).
    """
    cfg = await load_config(db)
    cfg = await _maybe_refresh_me_token(db, cfg)
    token = cfg.melhor_envio_token or settings.melhor_envio_token
    if not token:
        return {
            "results": [
                {"number": n, "ok": False, "message": "Configure o token do Melhor Envio no menu Frete."}
                for n in order_numbers
            ]
        }

    base = _me_base(cfg)
    origin = cfg.origin_zip or settings.shipping_origin_zip
    pkg = cfg.default_package
    if len(_digits(cfg.sender_cpf)) != 11:
        return {
            "results": [
                {"number": n, "ok": False, "message": "Informe o CPF do remetente no menu Frete."}
                for n in order_numbers
            ]
        }
    from_block = await _me_from_block(db, cfg, origin)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": settings.melhor_envio_user_agent,
    }

    results: list[dict] = []
    async with httpx.AsyncClient(timeout=40, headers=headers) as c:
        for number in order_numbers:
            try:
                results.append(
                    await _me_label_for_order(c, base, db, number, from_block, pkg, buy=buy)
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Melhor Envio: erro no pedido %s", number)
                results.append({"number": number, "ok": False, "message": f"Erro inesperado: {exc}"})
    await db.flush()
    return {"results": results}


async def poll_melhor_envio_tracking(db: AsyncSession) -> dict:
    """Consulta o Melhor Envio para todos os pedidos que já têm um envio (etiqueta)
    associado, preenche o código de rastreio e avança o status do pedido
    (`em separação` → `enviado` → `entregue`). Feito para rodar em rotina.

    O casamento pedido↔etiqueta é pelo `shipment_id` que a loja guarda ao criar o
    carrinho no ME — não depende de webhook."""
    from sqlalchemy import or_

    from app.modules.orders.models import Order

    cfg = await load_config(db)
    cfg = await _maybe_refresh_me_token(db, cfg)
    token = cfg.melhor_envio_token or settings.melhor_envio_token
    if not token:
        return {"ran": False, "reason": "sem token do Melhor Envio"}

    rows = list(
        await db.scalars(
            select(Order).where(
                Order.shipping_service_json["shipment_id"].astext.isnot(None),
                Order.status.notin_(("canceled", "refunded", "delivered")),
                or_(
                    Order.shipping_service_json["tracking_code"].astext.is_(None),
                    Order.shipping_service_json["me_tracking_status"].astext.is_(None),
                    Order.shipping_service_json["me_tracking_status"].astext != "delivered",
                ),
            )
        )
    )
    if not rows:
        return {"ran": True, "checked": 0, "updated": 0}

    by_shipment = {
        (o.shipping_service_json or {}).get("shipment_id"): o
        for o in rows
        if (o.shipping_service_json or {}).get("shipment_id")
    }
    ids = list(by_shipment)
    base = _me_base(cfg)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": settings.melhor_envio_user_agent,
    }
    updated = 0
    errors = 0
    async with httpx.AsyncClient(timeout=40, headers=headers) as c:
        # 1) tenta o lote — rápido, mas o `status` costuma atrasar
        batch: dict[str, dict] = {}
        for chunk_start in range(0, len(ids), 40):
            chunk = ids[chunk_start : chunk_start + 40]
            try:
                r = await c.post(
                    f"{base}/api/v2/me/shipment/tracking", json={"orders": chunk}
                )
                if r.status_code < 300 and r.content:
                    got = r.json()
                    if isinstance(got, dict):
                        batch.update({k: v for k, v in got.items() if isinstance(v, dict)})
            except Exception:  # noqa: BLE001
                logger.exception("poll ME: falha no lote de rastreio")

        # 2) confirma cada envio pelo /me/orders/{id} — este traz o status REAL
        #    (posted/delivered/canceled) e o rastreio, sem o atraso do lote.
        for sid, order in by_shipment.items():
            info = dict(batch.get(sid) or {})
            try:
                r = await c.get(f"{base}/api/v2/me/orders/{sid}")
                if r.status_code < 300 and r.content:
                    od = r.json()
                    if isinstance(od, dict):
                        info.update({k: v for k, v in od.items() if v is not None})
            except Exception:  # noqa: BLE001
                logger.exception("poll ME: falha ao consultar envio %s", sid)
                errors += 1

            if not info:
                continue
            code = info.get("tracking") or info.get("melhorenvio_tracking")
            me_status = (info.get("status") or "").lower()
            # timestamps mandam mais que o campo `status` (que às vezes atrasa)
            if info.get("delivered_at"):
                me_status = "delivered"
            elif info.get("canceled_at"):
                me_status = "canceled"
            elif not me_status and info.get("posted_at"):
                me_status = "posted"

            # Envio que ficou "aguardando pagamento no ME" e agora foi pago lá
            # (status released/paid ou já tem rastreio/geração): busca o PDF da
            # etiqueta para aparecer também no nosso painel.
            _svc = dict(order.shipping_service_json or {})
            _paid_in_me = bool(
                code
                or info.get("generated_at")
                or info.get("paid_at")
                or me_status in ("released", "paid", "posted", "delivered", "in_transit")
            )
            if _paid_in_me and not _svc.get("label_url"):
                try:
                    await c.post(f"{base}/api/v2/me/shipment/generate", json={"orders": [sid]})
                    pr = await c.post(
                        f"{base}/api/v2/me/shipment/print",
                        json={"mode": "public", "orders": [sid]},
                    )
                    if pr.status_code < 300:
                        url = (pr.json() or {}).get("url")
                        if url:
                            _svc["label_url"] = url
                            _svc["me_status"] = "label_ready"
                            order.shipping_service_json = _svc
                            updated += 1
                except Exception:  # noqa: BLE001
                    logger.exception("poll ME: falha ao gerar/imprimir etiqueta %s", sid)

            if await _me_apply_tracking(
                db, order, tracking_code=code, me_status=me_status or None, source="rotina"
            ):
                updated += 1

    await db.flush()
    return {"ran": True, "checked": len(ids), "updated": updated, "errors": errors}
