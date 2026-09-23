"""Regra de negócio do módulo `shipping` — cotação com cache Redis + rastreio."""
from __future__ import annotations

import asyncio
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
from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.errors import DomainError
from app.core.events import emit
from app.core.redis import redis_client
from app.modules.shipping.config import ShippingConfig
from app.modules.shipping.models import ShippingQuote
from app.modules.shipping.providers.base import Package, ShippingProvider, TrackingUpdate
from app.modules.shipping.providers.frenet import FrenetProvider
from app.modules.shipping.providers.melhor_envio import MelhorEnvioProvider

logger = logging.getLogger("shipping.service")

_CACHE_PREFIX = "ship:quote:"
_PROVIDERS: dict[str, type[ShippingProvider]] = {
    "melhor_envio": MelhorEnvioProvider,
    "frenet": FrenetProvider,
}

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
    if cfg.active_provider == "frenet":
        return FrenetProvider(
            token=cfg.frenet_token,
            partner_token=cfg.frenet_partner_token,
            webhook_header_name=cfg.frenet_webhook_header_name,
            webhook_header_value=cfg.frenet_webhook_header_value,
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
    """A compra falhou por falta de saldo na carteira do Melhor Envio?

    O ME varia bastante a frase, ex.: "Seu saldo de R$ 0.00 é insuficiente
    para o pagamento com a carteira no valor de R$ 47.79". Em vez de listar
    todas, também aceitamos "saldo" + "insuficiente" (pt) ou "insufficient"
    + "balance/funds/wallet" (en) aparecendo juntos, em qualquer ordem.
    """
    blob = (r.text or "").lower()
    try:
        data = r.json()
        blob += " " + (data if isinstance(data, str) else json.dumps(data)).lower()
    except Exception:  # noqa: BLE001
        pass
    if any(h in blob for h in _NO_BALANCE_HINTS):
        return True
    if "saldo" in blob and ("insuficiente" in blob or "insuficiência" in blob):
        return True
    return "insufficient" in blob and any(w in blob for w in ("balance", "funds", "wallet"))


# O ME recusa o checkout quando o `shipment_id` guardado no pedido não está mais
# no carrinho da conta (lojista apagou lá) ou já foi pago numa compra anterior.
# Mensagem típica: "Existe uma ou mais orders que já foram pagas ou inválidas."
_INVALID_ORDER_HINTS = (
    "pagas ou inválidas",
    "pagas ou invalidas",
    "already been paid",
    "já foram pagas",
    "ja foram pagas",
    "uma ou mais orders",
    "order inválida",
    "order invalida",
    "invalid order",
)


def _me_is_invalid_orders(r: httpx.Response) -> bool:
    """O checkout falhou porque o envio guardado não existe mais / já foi pago?"""
    blob = (r.text or "").lower()
    try:
        data = r.json()
        blob += " " + (data if isinstance(data, str) else json.dumps(data)).lower()
    except Exception:  # noqa: BLE001
        pass
    return any(h in blob for h in _INVALID_ORDER_HINTS)


def _me_pick_order(checkout: dict, shipment_id: str) -> dict:
    purchase = (checkout or {}).get("purchase") or checkout or {}
    orders = purchase.get("orders") or []
    for o in orders:
        if str(o.get("id")) == str(shipment_id):
            return o
    return orders[0] if orders else {}


def _svc_public(svc: dict) -> dict:
    # `shipment_id`/`me_status` são do Melhor Envio; a Frenet usa chaves
    # próprias (`frenet_shipment_id`/`frenet_tracking_status`) pra não colidir
    # com a rotina/consulta do ME (ver `poll_frenet_tracking`) -- aqui só
    # soma um fallback aditivo pra exibição funcionar pros dois.
    return {
        "shipment_id": svc.get("shipment_id") or svc.get("frenet_shipment_id"),
        "protocol": svc.get("protocol"),
        "tracking_code": svc.get("tracking_code"),
        "label_url": svc.get("label_url"),
        "me_status": svc.get("me_status") or svc.get("frenet_tracking_status"),
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
        # Vazio de propósito: o Melhor Envio imprime esse telefone na etiqueta
        # ("REMETENTE: ..., Tel: ...") e não queremos esse dado ali.
        "phone": "",
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

    # Registrado só no fim da função (depois do "status_changed" abaixo, se
    # houver um) para a linha do tempo mostrar "Rastreio disponível" antes de
    # "Rastreio adicionado" — a mudança de status é o evento principal dessa
    # dupla, o código em si é o detalhe.
    tracking_added_msg: str | None = None
    if tracking_code and svc.get("tracking_code") != tracking_code:
        svc["tracking_code"] = tracking_code
        order.shipping_service_json = svc
        changed = True
        tracking_added_msg = f"Código de rastreio do Melhor Envio: {tracking_code}"

    async def _flush_tracking_added() -> None:
        if tracking_added_msg:
            await record_event(
                db, order, type="tracking_added", actor_type="system",
                message=tracking_added_msg,
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
            # commit ANTES de emitir: o handler do e-mail abre a própria sessão
            # e precisa enxergar o rastreio/status JÁ gravados (mesmo motivo de
            # `orders.service.transition`).
            await db.commit()
            await emit("order.status_changed", {"order_id": str(order.id), "status": "in_transit"})

    # envio cancelado/expirado no ME não mexe no status do pedido da loja
    if me_norm in {"canceled", "cancelled", "expired"}:
        await _flush_tracking_added()
        return changed

    # só avança o status de pedido já pago (nunca de um pedido não pago)
    if order.status not in {"paid", "processing", "tracking_available", "shipped"}:
        await _flush_tracking_added()
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
        await _flush_tracking_added()
        # commit ANTES de emitir (mesmo motivo do bloco "in_transit" acima) --
        # senão o e-mail de "rastreio disponível"/"enviado" sai sem o código.
        await db.commit()
        await emit("order.status_changed", {"order_id": str(order.id), "status": target})
        changed = True
        return changed
    await _flush_tracking_added()
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
    _fresh_retry: bool = False,
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
    created_now = False

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
        created_now = True

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
    # O envio guardado no pedido não está mais no carrinho do ME (o lojista
    # apagou lá) ou já foi pago numa tentativa anterior. Se não acabamos de
    # criá-lo agora, descarta os ids velhos e refaz do zero (carrinho -> compra)
    # uma única vez — assim o "reenviar" volta a funcionar depois de excluir o
    # envio no painel do Melhor Envio.
    if (
        r.status_code >= 300
        and _me_is_invalid_orders(r)
        and not created_now
        and not _fresh_retry
    ):
        for k in ("shipment_id", "protocol", "tracking_code", "me_status", "me_reminder"):
            svc.pop(k, None)
        order.shipping_service_json = dict(svc)
        await db.flush()
        return await _me_label_for_order(
            c, base, db, number, from_block, pkg, buy=buy, _fresh_retry=True
        )

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


async def _render_url_to_pdf(
    url: str, *, postal_card: bool, want_declaration: bool, want_romaneio: bool = False
) -> bytes:
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

            # A geração da etiqueta no ME é assíncrona -- pode não estar
            # pronta ainda. NÃO fica tentando de novo aqui dentro (isso é
            # chamado de forma síncrona por um clique no admin -- ficar
            # recarregando a página por dezenas de segundos faz o navegador
            # desistir com "Failed to fetch" mesmo com o servidor terminando
            # a operação em segundo plano). Falha rápido; quem tenta de novo
            # automaticamente é a rotina periódica (`sync_reverse_tracking`/
            # `poll_melhor_envio_tracking`), que roda em background e não tem
            # esse limite de tempo.
            body = (await page.inner_text("body")).lower()
            if "destinat" not in body and "recebedor" not in body and "remetente" not in body:
                raise DomainError(
                    "O Melhor Envio não renderizou a etiqueta (a etiqueta pode ainda "
                    "estar sendo gerada — a sincronização automática tenta de novo sozinha).",
                    code="me_pdf_empty",
                )

            # opções da página de impressão do ME
            await _me_set_checkbox(page, "#postal_card", postal_card)        # 10x15
            await _me_set_checkbox(page, "#print_tags", True)               # etiqueta
            await _me_set_checkbox(page, "#print_daces", want_declaration)  # DACE simples
            await _me_set_checkbox(page, "#print_complete_daces", False)    # nunca a completa
            await _me_set_checkbox(page, "#print_packing_lists", want_romaneio)  # romaneio (itens do pedido)
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


async def _mark_labels_printed(db: AsyncSession, order_numbers: list[str]) -> None:
    """Registra a 1ª vez que a etiqueta de cada pedido foi baixada/impressa
    pelo painel — usado só pra exibição (coluna Etiqueta), não muda status."""
    from app.modules.orders.models import Order
    from app.modules.orders.service import record_event

    rows = list(await db.scalars(select(Order).where(Order.number.in_(order_numbers))))
    now = datetime.now(UTC).isoformat()
    for order in rows:
        svc = dict(order.shipping_service_json or {})
        if svc.get("label_printed_at"):
            continue
        svc["label_printed_at"] = now
        order.shipping_service_json = svc
        await record_event(
            db, order, type="label_printed", actor_type="admin",
            message="Etiqueta baixada/impressa pelo painel.",
        )


async def melhor_envio_labels_pdf(db: AsyncSession, order_numbers: list[str]) -> bytes:
    """PDF das etiquetas dos pedidos, pronto para baixar no painel da loja
    (sem abrir o site do Melhor Envio). Respeita o formato e a opção de
    Declaração de Conteúdo definidos no menu Frete.

    Buffer local de 1h (mesmo conjunto de pedidos + formato + declaração) --
    um "cache hit" nem chega a chamar a API do Melhor Envio (não só evita o
    Playwright, evita a dependência da etiqueta ainda existir lá)."""
    from app.modules.shipping import label_buffer

    cfg = await load_config(db)
    fmt = cfg.label_format or "termica_10x15"
    want_declaration = bool(cfg.print_declaration)
    buf_key = label_buffer.compute_key(order_numbers, fmt, want_declaration)
    cached = label_buffer.read_buffer(buf_key)
    if cached is not None:
        await _mark_labels_printed(db, order_numbers)
        return cached

    url = await melhor_envio_print_url(db, order_numbers)
    pdf = await _render_url_to_pdf(
        url,
        postal_card=(fmt != "a4_4up"),
        want_declaration=want_declaration,
    )
    if fmt == "a4_4up":
        pdf = _labels_a4_4up(pdf)
    label_buffer.write_buffer(buf_key, pdf)
    await _mark_labels_printed(db, order_numbers)
    return pdf


async def melhor_envio_label_pages_for_nfe_merge(db: AsyncSession, order_numbers: list[str]) -> bytes:
    """Etiquetas SEMPRE 10x15 (compactas, sem o romaneio do Melhor Envio --
    ligar o romaneio deles faz a própria página crescer bem além de 10x15,
    pra caber a tabela e a DACE), uma página por pedido, na MESMA ordem de
    `order_numbers` -- usado pelo "Gerar Etq/NFe" (`orders.etiqueta_nfe`)
    pra empilhar a tarja da NF-e embaixo de cada etiqueta (etiqueta
    intocada, a página cresce pra caber as duas). Não mexe no fluxo de
    etiqueta comum (`melhor_envio_labels_pdf`)."""
    url = await melhor_envio_print_url(db, order_numbers)
    pdf = await _render_url_to_pdf(
        url, postal_card=True, want_declaration=False, want_romaneio=False
    )
    await _mark_labels_printed(db, order_numbers)
    return pdf


async def generate_reverse_label(
    db: AsyncSession, number: str, *, background: BackgroundTasks | None = None
) -> dict:
    """Logística reversa (devolução): gera uma etiqueta no Melhor Envio com
    remetente = CLIENTE e destinatário = LOJA — mesma sequência de chamadas
    (carrinho -> checkout -> generate -> imprimir) do envio normal, só com
    os endereços invertidos. Nunca mexe em `shipping_service_json` (o envio
    de ida); tudo fica em `reverse_shipping_json`, um campo separado.

    Com saldo no Melhor Envio: compra, gera e já salva o PDF (Storage
    privado, nunca `/media` público) e o pedido avança pra "returning". Sem
    saldo: fica no carrinho do ME (`me_status=awaiting_me_payment`), igual o
    envio normal, e o pedido não muda de status ainda.
    """
    from sqlalchemy.orm import selectinload

    from app.core.events import emit
    from app.modules.orders.models import Order
    from app.modules.orders.service import record_event, transition
    from app.shared.storage import private_storage

    order = await db.scalar(
        select(Order).where(Order.number == number).options(selectinload(Order.items))
    )
    if not order:
        raise DomainError("Pedido não encontrado.", code="order_not_found")
    # Pode gerar de novo quantas vezes precisar (ex.: cancelou a etiqueta
    # anterior no painel do ME e quer refazer) -- cada chamada cria um envio
    # NOVO de verdade no Melhor Envio (cobra de novo do saldo, se comprar);
    # o que valer pro pedido é sempre o último `reverse_shipping_json`
    # salvo, sobrescrevendo o anterior.

    addr = order.shipping_address_json or {}
    _req = ("street", "number", "district", "city", "state", "zip")
    _missing = [k for k in _req if not str(addr.get(k) or "").strip()]
    if _missing:
        raise DomainError(
            f"Endereço do cliente incompleto para a logística reversa (falta: {', '.join(_missing)}).",
            code="reverse_missing_address",
        )
    cpf = _digits(order.cpf or addr.get("cpf") or "")
    if len(cpf) != 11:
        raise DomainError(
            "CPF do cliente ausente/inválido — não é possível gerar a logística reversa.",
            code="reverse_missing_cpf",
        )

    cfg = await load_config(db)
    cfg = await _maybe_refresh_me_token(db, cfg)
    token = cfg.melhor_envio_token or settings.melhor_envio_token
    if not token:
        raise DomainError("Configure o token do Melhor Envio no menu Frete.", code="me_no_token")
    base = _me_base(cfg)
    store_zip = cfg.origin_zip or settings.shipping_origin_zip
    pkg = cfg.default_package
    customer_zip = _digits(addr.get("zip", ""))

    # cotação: origem = cliente, destino = loja — pega a tarifa mais barata
    # entre os serviços permitidos (mesma regra do frete normal da loja).
    provider = MelhorEnvioProvider(token=token, base_url=base)
    rate_objs = await provider.quote(
        origin_zip=customer_zip,
        dest_zip=store_zip,
        packages=[Package(pkg.weight_grams, pkg.length_mm, pkg.width_mm, pkg.height_mm)],
    )
    allowed = {s.strip().lower() for s in (cfg.allowed_services or []) if s.strip()}
    rates = [r.as_dict() for r in rate_objs]
    eligible = [r for r in rates if _service_allowed(r, allowed)] or rates
    if not eligible:
        raise DomainError(
            "Melhor Envio não retornou nenhuma tarifa para o CEP do cliente.", code="reverse_no_rate"
        )
    rate = min(eligible, key=lambda r: r["price_cents"])
    service_id = rate["id"]

    from_block = {
        "name": addr.get("recipient_name") or order.email,
        "phone": _digits(addr.get("phone", "")),
        "email": order.email,
        "document": cpf,
        "address": addr.get("street", ""),
        "number": str(addr.get("number", "")),
        "complement": addr.get("complement") or "",
        "district": addr.get("district", ""),
        "city": addr.get("city", ""),
        "state_abbr": (addr.get("state") or "").upper()[:2],
        "country_id": "BR",
        "postal_code": customer_zip,
    }
    # destinatário = a loja — reaproveita a MESMA função do envio normal,
    # sem alterá-la.
    to_block = await _me_from_block(db, cfg, store_zip)

    total_qty = sum(i.quantity for i in order.items) or 1
    svc: dict = {"created_at": datetime.now(UTC).isoformat()}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": settings.melhor_envio_user_agent,
    }
    label_url: str | None = None

    async with httpx.AsyncClient(timeout=40, headers=headers) as c:
        cart_payload = {
            "service": int(service_id) if str(service_id).isdigit() else service_id,
            "from": from_block,
            "to": to_block,
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
                    "height": max(1, round(pkg.height_mm / 10)),
                    "width": max(1, round(pkg.width_mm / 10)),
                    "length": max(1, round(pkg.length_mm / 10)),
                    "weight": round(max(1, pkg.weight_grams) * total_qty / 1000, 3),
                }
            ],
            "options": {
                "insurance_value": round(order.grand_total_cents / 100, 2),
                "receipt": False,
                "own_hand": False,
                "reminder": f"Devolução pedido {number}",
                "platform": "Loja - logística reversa",
                "tags": [{"tag": f"devolucao-{number}", "url": None}],
            },
        }
        r = await c.post(f"{base}/api/v2/me/cart", json=cart_payload)
        if r.status_code >= 300:
            raise DomainError(_me_err("carrinho (devolução)", r), code="reverse_cart_failed")
        shipment_id = str((r.json() or {}).get("id") or "")
        if not shipment_id:
            raise DomainError(
                "Melhor Envio não retornou o id do envio de devolução.", code="reverse_cart_failed"
            )
        svc["shipment_id"] = shipment_id
        svc["me_status"] = "cart"

        r = await c.post(f"{base}/api/v2/me/shipment/checkout", json={"orders": [shipment_id]})
        if r.status_code >= 300:
            if _me_is_no_balance(r):
                svc["me_status"] = "awaiting_me_payment"
                order.reverse_shipping_json = dict(svc)
                await record_event(
                    db, order, type="reverse_label_cart", actor_type="admin",
                    message=(
                        "Logística reversa criada no carrinho do Melhor Envio — "
                        "sem saldo, aguardando pagamento no painel do ME."
                    ),
                )
                return {"ok": True, "awaiting_payment": True, **svc}
            raise DomainError(_me_err("compra (devolução)", r), code="reverse_checkout_failed")

        checkout: dict = {}
        try:
            checkout = r.json()
        except Exception:  # noqa: BLE001
            pass
        po = _me_pick_order(checkout, shipment_id)
        protocol = ((checkout.get("purchase") or {}).get("protocol")) or po.get("protocol")
        if protocol:
            svc["protocol"] = protocol
        svc["me_status"] = "purchased"
        order.reverse_shipping_json = dict(svc)
        # Registra e avança o pedido pra "returning" JÁ AQUI, assim que a
        # compra é confirmada -- não espera o PDF (que pode falhar/demorar,
        # é assíncrono do lado do ME e não deveria travar o fato de que a
        # devolução já foi comprada de verdade). Commit imediato: se o passo
        # do PDF adiante falhar/estourar, essa parte já fica valendo.
        await record_event(
            db, order, type="reverse_label_generated", actor_type="admin",
            message=f"Logística reversa comprada no Melhor Envio (protocolo {protocol})."
            if protocol else "Logística reversa comprada no Melhor Envio.",
        )
        await transition(db, order, "returning", actor_type="system", message="Logística reversa comprada.")

        await c.post(f"{base}/api/v2/me/shipment/generate", json={"orders": [shipment_id]})

        r = await c.post(f"{base}/api/v2/me/shipment/print", json={"mode": "public", "orders": [shipment_id]})
        if r.status_code < 300:
            try:
                label_url = (r.json() or {}).get("url")
            except Exception:  # noqa: BLE001
                pass

        r = await c.post(f"{base}/api/v2/me/shipment/tracking", json={"orders": [shipment_id]})
        if r.status_code < 300:
            try:
                info = (r.json() or {}).get(shipment_id) or {}
                if info.get("tracking"):
                    svc["tracking_code"] = info["tracking"]
            except Exception:  # noqa: BLE001
                pass

    if not label_url:
        # comprada, mas o link de impressão falhou — não trava a compra (já
        # registrada e com status avançado acima), só não tem PDF ainda.
        # Sem evento próprio na linha do tempo (o "comprada" acima já conta a
        # história; isso ficaria repetitivo/alarmante). Não espera o próximo
        # ciclo da rotina geral (5+ min): dispara um monitor de curto prazo
        # em segundo plano (tenta de novo a cada ~20s por alguns minutos).
        order.reverse_shipping_json = dict(svc)
        await db.commit()
        if background is not None:
            background.add_task(_watch_reverse_label_pdf, number)
        return {"ok": True, "label_pdf": False, **svc}

    try:
        pdf = await _render_url_to_pdf(label_url, postal_card=True, want_declaration=False)
    except DomainError:
        order.reverse_shipping_json = dict(svc)
        await db.commit()
        if background is not None:
            background.add_task(_watch_reverse_label_pdf, number)
        return {"ok": True, "label_pdf": False, **svc}
    key = f"orders/{number}/reverse-label.pdf"
    private_storage.save(key, pdf, "application/pdf")
    svc["reverse_label_key"] = key
    order.reverse_shipping_json = dict(svc)

    tracking_code = svc.get("tracking_code")
    msg = "PDF da etiqueta de logística reversa pronto para download."
    if tracking_code:
        msg += f" Código de rastreio: {tracking_code}."
    await record_event(db, order, type="reverse_label_pdf_ready", actor_type="admin", message=msg)
    # commit ANTES de emitir -- o e-mail (subscriber de `order.reverse_label_ready`)
    # abre a própria sessão e precisa enxergar o `reverse_label_key` já gravado.
    await db.commit()
    await emit("order.reverse_label_ready", {"order_id": str(order.id)})

    return {"ok": True, "label_pdf": True, **svc}


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


async def _try_complete_reverse_pdf(db: AsyncSession, c: httpx.AsyncClient, base: str, order) -> bool:
    """Tenta pegar o link de impressão + renderizar o PDF de uma logística
    reversa já comprada, sem comprar nada de novo. Usada tanto pela rotina
    periódica (`sync_reverse_tracking`) quanto pelo monitor de curto prazo
    logo após a geração (`_watch_reverse_label_pdf`) -- mesma lógica, dois
    ritmos de chamada diferentes."""
    from app.modules.orders.service import record_event
    from app.shared.storage import private_storage

    svc = dict(order.reverse_shipping_json or {})
    sid = svc.get("shipment_id")
    if not sid or svc.get("reverse_label_key"):
        return False
    try:
        r = await c.post(f"{base}/api/v2/me/shipment/print", json={"mode": "public", "orders": [sid]})
        label_url = (r.json() or {}).get("url") if r.status_code < 300 else None
    except Exception:  # noqa: BLE001
        logger.exception("logística reversa: falha ao pegar link de impressão do envio %s", sid)
        return False
    if not label_url:
        return False
    try:
        pdf = await _render_url_to_pdf(label_url, postal_card=True, want_declaration=False)
    except DomainError:
        return False  # ainda não saiu -- tenta de novo na próxima chamada
    except Exception:  # noqa: BLE001
        logger.exception("logística reversa: falha ao renderizar PDF do envio %s", sid)
        return False
    key = f"orders/{order.number}/reverse-label.pdf"
    private_storage.save(key, pdf, "application/pdf")
    svc["reverse_label_key"] = key
    order.reverse_shipping_json = svc
    await record_event(
        db, order, type="reverse_label_pdf_ready", actor_type="system",
        message="PDF da etiqueta de logística reversa pronto para download.",
    )
    await db.commit()
    await emit("order.reverse_label_ready", {"order_id": str(order.id)})
    return True


async def _watch_reverse_label_pdf(number: str) -> None:
    """Logo após gerar a logística reversa (compra confirmada mas PDF ainda
    não saiu), monitora de perto por alguns minutos -- não faz sentido
    esperar o próximo ciclo da rotina geral (5+ min) pra isso, já que a
    etiqueta costuma ficar pronta no Melhor Envio pouco depois da compra.
    Roda em segundo plano (`BackgroundTasks`), nunca bloqueia a resposta do
    clique de "Gerar logística reversa"."""
    from app.modules.orders.models import Order

    # 10 tentativas, ~20s de intervalo -- cobre os primeiros ~3-4 min, que é
    # onde a etiqueta normalmente fica pronta; depois disso a rotina geral
    # (a cada poucos minutos) continua tentando sozinha até conseguir.
    for _attempt in range(10):
        await asyncio.sleep(20)
        try:
            async with SessionLocal() as db:
                order = await db.scalar(select(Order).where(Order.number == number))
                if not order:
                    return
                svc = order.reverse_shipping_json or {}
                if svc.get("reverse_label_key") or not svc.get("shipment_id"):
                    return  # já saiu (por essa via ou outra) ou não há o que buscar

                cfg = await load_config(db)
                cfg = await _maybe_refresh_me_token(db, cfg)
                token = cfg.melhor_envio_token or settings.melhor_envio_token
                if not token:
                    return
                base = _me_base(cfg)
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": settings.melhor_envio_user_agent,
                }
                async with httpx.AsyncClient(timeout=40, headers=headers) as c:
                    done = await _try_complete_reverse_pdf(db, c, base, order)
                if done:
                    return
        except Exception:  # noqa: BLE001 - nunca deixa a task de fundo morrer com traceback perdido
            logger.exception("monitor pós-geração da logística reversa falhou (pedido %s)", number)


async def sync_reverse_tracking(db: AsyncSession) -> dict:
    """Acompanha os envios de logística reversa (devolução) em andamento:
    preenche o rastreio (a geração no ME é assíncrona, visto na prática
    testando o Sandbox — o código pode só sair minutos depois) e avança o
    status sozinho conforme os Correios confirmam:
      returning -> return_posted   (Correios confirma que foi postado)
      * -> returned                (Correios confirma entrega na loja)
    `returned` aqui já significa "devolução entregue" — não precisa mais de
    confirmação manual do lojista."""
    from app.modules.orders.models import Order
    from app.modules.orders.service import record_event, transition

    cfg = await load_config(db)
    cfg = await _maybe_refresh_me_token(db, cfg)
    token = cfg.melhor_envio_token or settings.melhor_envio_token
    if not token:
        return {"ran": False, "reason": "sem token do Melhor Envio"}

    rows = list(
        await db.scalars(
            select(Order).where(
                Order.status.in_(("returning", "return_posted")),
                Order.reverse_shipping_json["shipment_id"].astext.isnot(None),
            )
        )
    )
    # pedidos com etiqueta comprada mas cujo PDF não saiu na hora (geração
    # assíncrona do ME) -- entram na fila da rotina até conseguir. Pode
    # incluir pedidos já "returned" (a devolução chegou, mas o PDF em si
    # ainda vale a pena tentar completar pro histórico).
    pdf_pending_rows = list(
        await db.scalars(
            select(Order).where(
                Order.reverse_shipping_json["shipment_id"].astext.isnot(None),
                Order.reverse_shipping_json["reverse_label_key"].astext.is_(None),
            )
        )
    )
    if not rows and not pdf_pending_rows:
        return {"ran": True, "checked": 0, "updated": 0}

    base = _me_base(cfg)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": settings.melhor_envio_user_agent,
    }
    updated = 0
    async with httpx.AsyncClient(timeout=40, headers=headers) as c:
        for order in rows:
            svc = dict(order.reverse_shipping_json or {})
            sid = svc.get("shipment_id")
            if not sid:
                continue
            info: dict = {}
            try:
                r = await c.post(f"{base}/api/v2/me/shipment/tracking", json={"orders": [sid]})
                if r.status_code < 300 and r.content:
                    info.update((r.json() or {}).get(sid) or {})
            except Exception:  # noqa: BLE001
                logger.exception("sync reversa: falha no rastreio do envio %s", sid)
            try:
                r = await c.get(f"{base}/api/v2/me/orders/{sid}")
                if r.status_code < 300 and r.content:
                    od = r.json()
                    if isinstance(od, dict):
                        info.update({k: v for k, v in od.items() if v is not None})
            except Exception:  # noqa: BLE001
                logger.exception("sync reversa: falha ao consultar envio %s", sid)

            code = info.get("tracking") or info.get("melhorenvio_tracking")
            if code and svc.get("tracking_code") != code:
                svc["tracking_code"] = code
                order.reverse_shipping_json = svc
                await record_event(
                    db, order, type="reverse_tracking_added", actor_type="system",
                    message=f"Código de rastreio da devolução: {code}",
                )
                updated += 1

            me_status = (info.get("status") or "").lower()
            if info.get("delivered_at"):
                me_status = "delivered"
            elif info.get("posted_at") and not me_status:
                me_status = "posted"

            if me_status == "delivered" and order.status != "returned":
                await db.commit()
                await transition(
                    db, order, "returned", actor_type="system",
                    message="Correios confirmam: devolução entregue na loja.",
                )
                updated += 1
            elif me_status in ("posted", "in_transit") and order.status == "returning":
                await db.commit()
                await transition(
                    db, order, "return_posted", actor_type="system",
                    message="Correios confirmam: devolução postada pelo cliente.",
                )
                updated += 1

        # fila de PDF pendente: tenta de novo pegar o link de impressão +
        # renderizar, sem comprar nada de novo (a compra já foi feita).
        for order in pdf_pending_rows:
            if await _try_complete_reverse_pdf(db, c, base, order):
                updated += 1

    await db.flush()
    return {"ran": True, "checked": len(rows) + len(pdf_pending_rows), "updated": updated}


# --------------------------------------------------------------------- Etiqueta Frenet
# Tudo abaixo é paralelo ao bloco "Etiqueta Melhor Envio" acima -- funções
# novas, nada do bloco do ME foi alterado. A Frenet grava o id do envio e o
# status de rastreio em chaves PRÓPRIAS (`frenet_shipment_id`,
# `frenet_tracking_status`) em vez de `shipment_id`/`me_tracking_status` --
# se usasse as mesmas chaves do ME, a rotina `poll_melhor_envio_tracking`
# (que filtra por essas chaves) passaria a tentar consultar pedidos da
# Frenet na API do Melhor Envio. `tracking_code`/`label_url` são inertes pro
# ME (ele nunca seleciona pedidos por esses campos) e por isso continuam
# compartilhados, o que basta pra `_svc_public` e a tela do pedido mostrarem
# a etiqueta da Frenet sem mudança nenhuma no front.
def _frenet_mm_to_cm(mm: int) -> float:
    return round(max(mm, 1) / 10, 2)


def _frenet_g_to_kg(g: int) -> float:
    return round(max(g, 1) / 1000, 3)


def _frenet_address_block(addr: dict, fallback_zip: str) -> dict:
    return {
        "ZipCode": _digits(addr.get("zip") or fallback_zip),
        "City": addr.get("city", ""),
        "Street": addr.get("street", ""),
        "AddressNumber": str(addr.get("number", "")),
        "AddressComplement": addr.get("complement") or "",
        "AddressQuarter": addr.get("district", ""),
        "AddressState": (addr.get("state") or "").upper()[:2],
        "Country": "BR",
    }


async def _frenet_from_block(db: AsyncSession, cfg: ShippingConfig, origin: str) -> dict:
    """Remetente do envio Frenet = mesma fonte que `_me_from_block` usa
    (Aparência → Dados da loja + CPF do responsável, menu Frete)."""
    from app.modules.admin.models import StoreSettings

    st = (await db.scalars(select(StoreSettings))).first()
    sa = (st.address_json if st and st.address_json else {}) or {}
    cpf = _digits(cfg.sender_cpf)
    cnpj = _digits((st.cnpj if st else "") or "")
    return {
        "Name": (st.legal_name or st.store_name if st else None) or "Loja",
        "Email": settings.smtp_from_email,
        "Phone": "",
        "Document": cnpj if len(cnpj) == 14 else cpf,
        "Address": _frenet_address_block(sa, origin),
    }


async def _frenet_apply_tracking(
    db: AsyncSession,
    order,
    *,
    tracking_code: str | None,
    frenet_status: str | None,
    source: str = "etiqueta",
) -> bool:
    """Equivalente a `_me_apply_tracking`, só que pra Frenet -- função
    paralela (não reaproveita a do ME) por causa das chaves próprias citadas
    acima. Mesma régua `_ORDER_STATUS_RANK` (essa é genérica, compartilhada)."""
    from app.modules.orders.service import record_event

    changed = False
    svc = dict(order.shipping_service_json or {})

    tracking_added_msg: str | None = None
    if tracking_code and svc.get("tracking_code") != tracking_code:
        svc["tracking_code"] = tracking_code
        order.shipping_service_json = svc
        changed = True
        tracking_added_msg = f"Código de rastreio da Frenet: {tracking_code}"

    async def _flush_tracking_added() -> None:
        if tracking_added_msg:
            await record_event(
                db, order, type="tracking_added", actor_type="system",
                message=tracking_added_msg,
            )

    fr_norm = (frenet_status or "").upper()
    prev_fr = (svc.get("frenet_tracking_status") or "").upper()
    if frenet_status and prev_fr != fr_norm:
        svc["frenet_tracking_status"] = frenet_status
        order.shipping_service_json = svc
        changed = True
        if fr_norm == "EM_TRANSITO" and order.status == "shipped":
            await record_event(
                db, order, type="tracking_update", actor_type="system",
                message="Frenet: objeto em trânsito.",
            )
            await db.commit()
            await emit("order.status_changed", {"order_id": str(order.id), "status": "in_transit"})

    if order.status not in {"paid", "processing", "tracking_available", "shipped"}:
        await _flush_tracking_added()
        return changed

    has_tracking = bool(tracking_code or svc.get("tracking_code"))
    if fr_norm == "ENTREGUE":
        target = "delivered"
    elif fr_norm in {"POSTADO", "EM_TRANSITO"}:
        target = "shipped"
    elif has_tracking:
        target = "tracking_available"
    elif svc.get("frenet_shipment_id"):
        target = "processing"
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
            message=f"Frenet ({source}): pedido marcado como {_labels.get(target, target)}.",
            actor_type="system",
        )
        await _flush_tracking_added()
        await db.commit()
        await emit("order.status_changed", {"order_id": str(order.id), "status": target})
        changed = True
        return changed
    await _flush_tracking_added()
    return changed


async def _frenet_label_for_order(
    provider: FrenetProvider,
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

    service_code = svc.get("id")
    if not service_code or str(service_code) in {"free", "0"}:
        return {"number": number, "ok": False, "message": "Pedido sem serviço de frete selecionado."}

    addr = order.shipping_address_json or {}
    _req = ("street", "number", "district", "city", "state", "zip")
    _missing = [k for k in _req if not str(addr.get(k) or "").strip()]
    if _missing:
        return {
            "number": number, "ok": False,
            "message": f"Endereço de entrega do pedido incompleto (falta: {', '.join(_missing)}).",
        }

    shipment_id = svc.get("frenet_shipment_id")
    created_now = False

    if not shipment_id:
        total_qty = sum(it.quantity for it in order.items) or 1
        item_ids = [it.sku for it in order.items] or ["ITEM-1"]
        extra = svc.get("extra") or {}
        shipment = {
            "Order": {
                "Id": number,
                "Value": round(order.grand_total_cents / 100, 2),
                "Items": [
                    {
                        "OrderId": number,
                        "ItemId": it.sku,
                        "ProductName": (it.name or "Item")[:120],
                        "SKU": it.sku,
                        "Weight": _frenet_g_to_kg(getattr(pkg, "weight_grams", 300) or 300),
                        "Length": _frenet_mm_to_cm(getattr(pkg, "length_mm", 200) or 200),
                        "Height": _frenet_mm_to_cm(getattr(pkg, "height_mm", 100) or 100),
                        "Width": _frenet_mm_to_cm(getattr(pkg, "width_mm", 150) or 150),
                        "Quantity": it.quantity,
                        "Price": round(it.unit_price_cents / 100, 2),
                    }
                    for it in order.items
                ],
                "From": from_block,
                "To": {
                    "Name": addr.get("recipient_name") or order.email,
                    "Email": order.email,
                    "Phone": _digits(addr.get("phone", "")),
                    "Document": _digits(order.cpf or addr.get("cpf") or ""),
                    "Address": _frenet_address_block(addr, addr.get("zip", "")),
                },
            },
            "Volumes": [
                {
                    "Weight": round(
                        _frenet_g_to_kg(getattr(pkg, "weight_grams", 300) or 300) * total_qty, 3
                    ),
                    "Length": _frenet_mm_to_cm(getattr(pkg, "length_mm", 200) or 200),
                    "Height": _frenet_mm_to_cm(getattr(pkg, "height_mm", 100) or 100),
                    "Width": _frenet_mm_to_cm(getattr(pkg, "width_mm", 150) or 150),
                    "Price": round(order.grand_total_cents / 100, 2),
                    "DeclaredValue": round(order.grand_total_cents / 100, 2),
                    "OrderItemsId": item_ids,
                }
            ],
            "Quotation": {
                "ShippingServiceCode": service_code,
                "ShippingServiceName": svc.get("service", ""),
                "Carrier": svc.get("carrier", ""),
                "CarrierCode": extra.get("carrier_code"),
                "ShippingPrice": round((svc.get("price_cents") or 0) / 100, 2),
                "DeliveryTime": svc.get("delivery_days") or 0,
            },
        }
        try:
            created = await provider.create_shipment(shipment)
        except DomainError as exc:
            return {"number": number, "ok": False, "message": str(exc)}
        results = created if isinstance(created, list) else created.get("Results") or [created]
        first = (results or [{}])[0]
        shipment_id = first.get("ShipmentId") or first.get("Id")
        if not shipment_id:
            return {"number": number, "ok": False, "message": "Frenet não retornou o id do envio."}
        svc.update({"frenet_shipment_id": shipment_id, "frenet_tracking_status": "criado", "provider": "frenet"})
        order.shipping_service_json = dict(svc)
        created_now = True

    await _frenet_apply_tracking(
        db, order, tracking_code=None, frenet_status=None, source="etiqueta enviada"
    )

    if not buy:
        return {
            "number": number, "ok": True,
            "message": "Envio criado na Frenet (aguardando compra).",
            **_svc_public(svc),
        }

    try:
        checkout = await provider.checkout([int(shipment_id)] if str(shipment_id).isdigit() else [shipment_id])
    except DomainError as exc:
        return {"number": number, "ok": False, "message": str(exc)}

    if checkout.get("Status") == 2:
        svc["frenet_tracking_status"] = "aguardando_pagamento"
        order.shipping_service_json = dict(svc)
        return {
            "number": number, "ok": True,
            "message": (
                "Sem saldo/checkout pendente na Frenet — o envio foi criado. "
                "Finalize o pagamento no painel da Frenet; a etiqueta é sincronizada depois."
            ),
            **_svc_public(svc),
        }

    try:
        label = await provider.get_label(shipment_id)
    except DomainError as exc:
        return {"number": number, "ok": created_now, "message": str(exc), **_svc_public(svc)}

    label_url = label.get("LabelUrl")
    tracking_code = label.get("TrackingNumber") or svc.get("tracking_code")
    if tracking_code:
        svc["tracking_code"] = tracking_code
    if label_url:
        svc["label_url"] = label_url
        svc["frenet_tracking_status"] = "etiqueta_pronta"
    order.shipping_service_json = dict(svc)
    if order.fulfillment_status in {"unfulfilled", ""}:
        order.fulfillment_status = "partial"

    ok = bool(label_url)
    if ok:
        # status real da transportadora (não "inventa" POSTADO só por ter
        # código de rastreio -- ter o código não significa que já foi
        # coletado; mesmo raciocínio de `_me_label_for_order`, que passa
        # `me_status=svc.get("me_tracking_status")` aqui, não um valor fixo).
        await _frenet_apply_tracking(
            db, order, tracking_code=tracking_code, frenet_status=svc.get("frenet_tracking_status"),
            source="etiqueta gerada",
        )
    return {
        "number": number,
        "ok": ok,
        "message": "Etiqueta comprada e gerada." if ok else "Compra registrada, mas a etiqueta ainda não saiu.",
        **_svc_public(svc),
    }


async def send_orders_to_frenet(db: AsyncSession, order_numbers: list[str], *, buy: bool = True) -> dict:
    """Equivalente a `send_orders_to_melhor_envio`, pra Frenet."""
    cfg = await load_config(db)
    if not cfg.frenet_token:
        return {
            "results": [
                {"number": n, "ok": False, "message": "Configure o token da Frenet no menu Frete."}
                for n in order_numbers
            ]
        }
    if len(_digits(cfg.sender_cpf)) != 11:
        return {
            "results": [
                {"number": n, "ok": False, "message": "Informe o CPF do remetente no menu Frete."}
                for n in order_numbers
            ]
        }
    origin = cfg.origin_zip or settings.shipping_origin_zip
    pkg = cfg.default_package
    provider = FrenetProvider(
        token=cfg.frenet_token,
        partner_token=cfg.frenet_partner_token,
        webhook_header_name=cfg.frenet_webhook_header_name,
        webhook_header_value=cfg.frenet_webhook_header_value,
    )
    from_block = await _frenet_from_block(db, cfg, origin)

    results: list[dict] = []
    for number in order_numbers:
        try:
            results.append(await _frenet_label_for_order(provider, db, number, from_block, pkg, buy=buy))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Frenet: erro no pedido %s", number)
            results.append({"number": number, "ok": False, "message": f"Erro inesperado: {exc}"})
    await db.flush()
    return {"results": results}


async def frenet_labels_pdf(db: AsyncSession, order_numbers: list[str]) -> bytes:
    """Baixa e junta as etiquetas (já prontas em PDF/URL direta da Frenet --
    ao contrário do ME, que não expõe PDF por API e precisa ser renderizado
    via headless Chromium)."""
    from sqlalchemy.orm import selectinload

    from app.modules.orders.models import Order

    rows = list(
        await db.scalars(
            select(Order).where(Order.number.in_(order_numbers)).options(selectinload(Order.items))
        )
    )
    urls = [
        (o.shipping_service_json or {}).get("label_url")
        for o in rows
        if (o.shipping_service_json or {}).get("label_url")
    ]
    if not urls:
        raise DomainError("Nenhuma das etiquetas selecionadas está pronta ainda.", code="label_not_ready")

    pdfs: list[bytes] = []
    async with httpx.AsyncClient(timeout=30) as c:
        for url in urls:
            try:
                r = await c.get(url)
                if r.status_code < 300 and r.content:
                    pdfs.append(r.content)
            except Exception:  # noqa: BLE001
                logger.exception("Frenet: falha ao baixar etiqueta %s", url)

    if not pdfs:
        raise DomainError("Não foi possível baixar as etiquetas da Frenet agora.", code="shipping_unavailable")

    await _mark_labels_printed(db, order_numbers)
    if len(pdfs) == 1:
        return pdfs[0]
    try:
        from pypdf import PdfReader, PdfWriter

        writer = PdfWriter()
        for pdf in pdfs:
            for page in PdfReader(io.BytesIO(pdf)).pages:
                writer.add_page(page)
        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()
    except Exception:  # noqa: BLE001
        logger.exception("Frenet: falha ao juntar etiquetas em um único PDF")
        return pdfs[0]


async def poll_frenet_tracking(db: AsyncSession) -> dict:
    """Equivalente a `poll_melhor_envio_tracking`, pra Frenet. A Frenet não
    tem endpoint de consulta em lote (ao contrário do ME) -- consulta
    `tracking/trackinginfo` um envio de cada vez."""
    from app.modules.orders.models import Order

    cfg = await load_config(db)
    if not cfg.frenet_token:
        return {"ran": False, "reason": "sem token da Frenet"}

    rows = list(
        await db.scalars(
            select(Order).where(
                Order.shipping_service_json["frenet_shipment_id"].astext.isnot(None),
                Order.status.notin_(("canceled", "refunded", "delivered")),
                Order.shipping_service_json["frenet_tracking_status"].astext != "ENTREGUE",
            )
        )
    )
    if not rows:
        return {"ran": True, "checked": 0, "updated": 0}

    provider = FrenetProvider(
        token=cfg.frenet_token,
        partner_token=cfg.frenet_partner_token,
        webhook_header_name=cfg.frenet_webhook_header_name,
        webhook_header_value=cfg.frenet_webhook_header_value,
    )
    updated = 0
    errors = 0
    for order in rows:
        svc = dict(order.shipping_service_json or {})
        service_code = str(svc.get("id") or "")
        tracking_number = svc.get("tracking_code")
        if not service_code or not tracking_number:
            continue
        try:
            data = await provider.track(service_code=service_code, tracking_number=tracking_number)
        except Exception:  # noqa: BLE001
            logger.exception("poll Frenet: falha ao consultar %s", order.number)
            errors += 1
            continue
        update = provider.parse_webhook(
            {}, {"ShipmentId": svc.get("frenet_shipment_id"), "TrackingNumber": tracking_number, **data}
        )
        if update and await _frenet_apply_tracking(
            db, order, tracking_code=update.tracking_code, frenet_status=update.status, source="rotina"
        ):
            updated += 1

    await db.flush()
    return {"ran": True, "checked": len(rows), "updated": updated, "errors": errors}


async def handle_frenet_tracking_webhook(db: AsyncSession, headers: dict, raw_body: bytes, body: dict) -> dict:
    """Equivalente a `handle_tracking_webhook`, mas pra Frenet -- função
    paralela (não reaproveita a genérica) porque essa casa o pedido pelas
    chaves `frenet_shipment_id`/`tracking_code` em vez de `shipment_id`."""
    cfg = await load_config(db)
    provider = FrenetProvider(
        token=cfg.frenet_token,
        partner_token=cfg.frenet_partner_token,
        webhook_header_name=cfg.frenet_webhook_header_name,
        webhook_header_value=cfg.frenet_webhook_header_value,
    )
    if not provider.verify_webhook(headers, raw_body):
        raise DomainError("Assinatura de webhook inválida.", code="bad_signature")

    update = provider.parse_webhook(headers, body)
    if not update:
        return {"ignored": True}

    from app.modules.orders.models import Order

    order = None
    if update.provider_shipment_id:
        order = await db.scalar(
            select(Order).where(
                Order.shipping_service_json["frenet_shipment_id"].astext == update.provider_shipment_id
            )
        )
    if not order and update.tracking_code:
        order = await db.scalar(
            select(Order).where(
                Order.shipping_service_json["tracking_code"].astext == update.tracking_code
            )
        )
    if not order:
        logger.info("webhook Frenet sem pedido correspondente: %s", update)
        return {"matched": False}

    changed = await _frenet_apply_tracking(
        db, order, tracking_code=update.tracking_code, frenet_status=update.status, source="webhook"
    )
    return {"matched": True, "status": update.status, "tracking_saved": changed}
