"""Regra de negócio do módulo `payment` — cobrança, webhook idempotente,
reconciliação do pedido e reembolso."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import DomainError, NotFoundError, PaymentError, ValidationError
from app.core.events import emit
from app.modules.orders import service as orders_service
from app.modules.orders.models import Order
from app.modules.payment.config import PaymentConfig, ProviderEntry
from app.modules.payment.models import Payment, PaymentWebhookEvent
from app.modules.payment.providers.appmax import AppmaxGateway
from app.modules.payment.providers.base import CardInput, PaymentGateway
from app.modules.payment.providers.fake import FakeGateway

logger = logging.getLogger("payment.service")

_PROVIDERS: dict[str, type[PaymentGateway]] = {"appmax": AppmaxGateway, "fake": FakeGateway}

# status normalizado do gateway -> (payment.status, ação no pedido)
_ORDER_ACTION = {
    "paid": "paid",
    "pending": None,
    "failed": "cancel",
    "canceled": "cancel",
    "refunded": "refund",
    "chargeback": "refund",
}


def _migrate_legacy_config(raw: dict) -> dict:
    """Converte o formato antigo (`active_provider` único + `methods.*`
    booleanos) pro novo (`providers` com credenciais por provedor +
    `method_providers` por método) -- só na leitura, não grava sozinho (a
    primeira vez que o admin salvar algo já persiste no formato novo).
    Idempotente: se já está no formato novo, devolve como veio."""
    if "providers" in raw or "method_providers" in raw:
        return raw
    if "active_provider" not in raw and "appmax_access_token" not in raw:
        return raw  # config nova, nunca configurada -- usa os defaults do schema

    active = raw.get("active_provider") or "appmax"
    methods_raw = raw.get("methods") or {}
    providers = {
        "appmax": {
            "enabled": True,
            "config": {
                "access_token": raw.get("appmax_access_token", ""),
                "sandbox": raw.get("appmax_sandbox", True),
                "webhook_secret": raw.get("appmax_webhook_secret", ""),
            },
        },
        "fake": {"enabled": True, "config": {}},
    }
    method_providers = {
        m: active for m in ("credit_card", "pix", "boleto") if methods_raw.get(m, True)
    }
    return {
        "providers": providers,
        "method_providers": method_providers,
        "max_installments": raw.get("max_installments", 12),
    }


async def load_config(db: AsyncSession) -> PaymentConfig:
    from app.modules.admin.models import ModuleRow

    row = await db.get(ModuleRow, "payment")
    raw = dict(row.config_json) if row and row.config_json else {}
    return PaymentConfig(**_migrate_legacy_config(raw))


async def save_config(db: AsyncSession, patch: dict) -> PaymentConfig:
    from app.modules.admin.models import ModuleRow

    row = await db.get(ModuleRow, "payment")
    current = dict(row.config_json) if row and row.config_json else {}
    current = _migrate_legacy_config(current)
    for k, v in patch.items():
        if v is not None:
            current[k] = v
    cfg = PaymentConfig(**current)
    if row is None:
        row = ModuleRow(slug="payment", enabled=True, config_json=cfg.model_dump())
        db.add(row)
    else:
        row.config_json = cfg.model_dump()
    row.updated_at = datetime.now(UTC)
    await db.flush()
    return cfg


async def update_provider(db: AsyncSession, slug: str, *, enabled: bool | None, config_patch: dict) -> PaymentConfig:
    """Atualiza SÓ um provedor (liga/desliga + credenciais), sem mexer nos
    outros nem em `method_providers`. Campo de texto em branco = mantém o
    valor já salvo (mesmo padrão de segredo mascarado usado no resto do
    projeto) -- só sobrescreve o que veio preenchido de verdade."""
    if slug not in ("appmax", "fake"):
        raise ValidationError(f"Provedor de pagamento desconhecido: {slug}")
    cfg = await load_config(db)
    entry = cfg.providers.get(slug) or ProviderEntry()
    if enabled is not None:
        entry.enabled = enabled
    new_config = dict(entry.config)
    for k, v in (config_patch or {}).items():
        if v is not None and v != "":
            new_config[k] = v
    entry.config = new_config
    providers = {s: e.model_dump() for s, e in cfg.providers.items()}
    providers[slug] = entry.model_dump()
    return await save_config(db, {"providers": providers})


async def update_method_providers(db: AsyncSession, mapping: dict, max_installments: int | None) -> PaymentConfig:
    """Substitui o vínculo método -> provedor por inteiro (o formulário do
    admin sempre manda os 3 métodos de uma vez, não precisa de merge
    parcial). Valor vazio/None pro método = método desligado."""
    method_providers = {m: slug for m, slug in mapping.items() if slug}
    patch: dict = {"method_providers": method_providers}
    if max_installments is not None:
        patch["max_installments"] = max_installments
    return await save_config(db, patch)


def _build_gateway(cfg: PaymentConfig, slug: str) -> PaymentGateway:
    entry = cfg.providers.get(slug)
    if not entry or not entry.enabled:
        raise DomainError(f"Provedor de pagamento '{slug}' não está ativo.")
    if slug == "fake":
        return FakeGateway()
    if slug == "appmax":
        c = entry.config
        base = settings.appmax_api_url
        if not c.get("sandbox", True):
            base = base.replace("homolog.sandboxappmax.com.br", "admin.appmax.com.br")
        return AppmaxGateway(
            access_token=c.get("access_token") or settings.appmax_access_token,
            base_url=base,
            webhook_secret=c.get("webhook_secret") or settings.appmax_webhook_secret,
        )
    raise DomainError(f"Provedor de pagamento desconhecido: {slug}")


def _gateway_for_method(cfg: PaymentConfig, method: str) -> PaymentGateway:
    slug = cfg.method_providers.get(method)
    if not slug:
        raise ValidationError(f"Método '{method}' não está habilitado.")
    return _build_gateway(cfg, slug)


async def create_charge(
    db: AsyncSession, *, order_number: str, method: str, card: dict | None,
    background: BackgroundTasks | None = None,
) -> Payment:
    cfg = await load_config(db)
    if method not in ("credit_card", "pix", "boleto"):
        raise ValidationError("Método de pagamento inválido.")

    order = await orders_service.get_by_number(db, order_number)
    if order.status not in ("pending_payment",):
        raise ValidationError("Este pedido não está aguardando pagamento.")

    existing = await db.scalar(
        select(Payment).where(Payment.order_id == order.id, Payment.status.in_(("pending", "authorized", "paid")))
    )
    if existing and existing.status == "paid":
        return existing

    gateway = _gateway_for_method(cfg, method)
    card_input = CardInput(**card) if card else None
    charge = await gateway.create_charge(order=order, method=method, card=card_input)

    is_new = existing is None
    payment = existing or Payment(order_id=order.id)
    payment.provider = charge.provider
    payment.method = charge.method
    payment.status = charge.status if charge.status in ("pending", "paid", "failed") else "pending"
    payment.amount_cents = charge.amount_cents
    payment.installments = charge.installments
    payment.provider_charge_id = charge.provider_charge_id
    payment.provider_payload_json = charge.raw
    payment.pix_qr_code = charge.pix_qr_code
    payment.pix_expires_at = _parse_dt(charge.pix_expires_at)
    payment.boleto_url = charge.boleto_url
    payment.boleto_barcode = charge.boleto_barcode
    if charge.status == "paid":
        payment.paid_at = datetime.now(UTC)
    if is_new:
        db.add(payment)
    await db.flush()

    await _apply_status(db, order, payment, charge.status, source="charge", background=background)
    if payment.status == "failed":
        # o cartão foi recusado NA HORA (resposta síncrona do gateway) — devolve
        # erro HTTP (o front só nota "pagamento não autorizado" se a chamada
        # não vier com 2xx; um 200 com status "failed" no corpo passava batido
        # e o cliente caía na tela de "obrigado" com o pedido cancelado).
        raise PaymentError(
            _decline_message(charge) or "Pagamento recusado pela operadora do cartão."
        )
    return payment


def _decline_message(charge) -> str | None:
    """Melhor mensagem de recusa disponível na resposta do gateway."""
    raw = charge.raw or {}
    for key in ("text", "message", "status_text", "reason", "decline_reason"):
        v = raw.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _parse_dt(v: str | None):
    if not v:
        return None
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None


async def _apply_status(
    db: AsyncSession, order: Order, payment: Payment, normalized: str, *, source: str,
    background: BackgroundTasks | None = None,
) -> None:
    action = _ORDER_ACTION.get(normalized)
    if normalized == "paid":
        if payment.status == "paid" and order.payment_status == "paid":
            return  # idempotente: cobrança instantânea + webhook não devem duplicar
        payment.status = "paid"
        if not payment.paid_at:
            payment.paid_at = datetime.now(UTC)
        order.payment_status = "paid"
        await orders_service.finalize_paid(
            db, await orders_service._load(db, order.id), background=background
        )
    elif action == "cancel":
        payment.status = "failed"
        if order.status == "pending_payment":
            # sem isto, `order.payment_status` ficava para sempre em "pending"
            # numa recusa assíncrona (webhook) — a página de obrigado nunca via
            # o pagamento como recusado, só ficava "aguardando" indefinidamente.
            order.payment_status = "failed"
            await orders_service.transition(
                db, order, "canceled", actor_type="system",
                message=f"Pagamento não concluído ({source})", background=background,
            )
    elif action == "refund":
        payment.status = "refunded" if normalized == "refunded" else "chargeback"
        order.payment_status = payment.status
        if order.status not in ("refunded", "canceled"):
            try:
                await orders_service.transition(
                    db, order, "refunded", actor_type="system",
                    message=f"{normalized} ({source})", background=background,
                )
            except ValidationError:
                order.status = "refunded"
    await db.flush()


async def handle_webhook(
    db: AsyncSession, provider: str, headers: dict, raw_body: bytes, body: dict,
    *, background: BackgroundTasks | None = None,
) -> dict:
    cfg = await load_config(db)
    if provider not in _PROVIDERS:
        raise NotFoundError("Provedor de webhook desconhecido.")
    # usa o gateway do PRÓPRIO provedor que mandou o webhook (URL já carrega
    # o slug) -- antes usava sempre o "provedor ativo" global, que dava
    # errado assim que um método passasse a usar um provedor diferente.
    gateway = _build_gateway(cfg, provider)

    signature_valid = gateway.verify_webhook(headers, raw_body)
    result = gateway.parse_webhook(headers, body)
    if result is None:
        return {"ignored": True}
    result.signature_valid = signature_valid

    # idempotência
    dup = await db.scalar(
        select(PaymentWebhookEvent).where(
            PaymentWebhookEvent.provider == provider,
            PaymentWebhookEvent.provider_event_id == result.provider_event_id,
        )
    )
    if dup and dup.processed_at is not None:
        return {"duplicate": True}

    evt = dup
    if evt is None:
        evt = PaymentWebhookEvent(
            provider=provider,
            provider_event_id=result.provider_event_id,
            created_at=datetime.now(UTC),
        )
        db.add(evt)
        try:
            await db.flush()
        except IntegrityError:
            # concorrência: dois envios do MESMO evento quase simultâneos —
            # o outro já gravou a linha (constraint `idempotency`). Descarta
            # esta tentativa e trata como duplicado/já-em-processamento.
            await db.rollback()
            dup = await db.scalar(
                select(PaymentWebhookEvent).where(
                    PaymentWebhookEvent.provider == provider,
                    PaymentWebhookEvent.provider_event_id == result.provider_event_id,
                )
            )
            if dup and dup.processed_at is not None:
                return {"duplicate": True}
            evt = dup
            if evt is None:
                # não deveria acontecer (a constraint garante que a linha existe);
                # melhor sair sem processar do que estourar com AttributeError.
                logger.error("webhook %s: colisão de idempotência sem linha encontrada", provider)
                return {"ignored": True}
    evt.signature_valid = signature_valid
    evt.payload_json = body
    await db.flush()

    if not signature_valid:
        logger.warning("webhook %s com assinatura inválida", provider)
        raise PaymentError("Assinatura de webhook inválida.", code="bad_signature")

    effective_status = result.status
    if gateway.requires_status_confirmation:
        # provedor sem assinatura verificável (Appmax confirmada) -- o
        # payload do webhook em si não é confiável, só dispara a reconsulta.
        # Sem `provider_charge_id` ou se a reconsulta falhar, não aplica
        # nada agora: fica pendente pro próximo retry do gateway em vez de
        # marcar como pago/cancelado com base num payload não verificado.
        confirmed = (
            await gateway.confirm_status(result.provider_charge_id) if result.provider_charge_id else None
        )
        if confirmed is None:
            logger.warning(
                "webhook %s: não deu pra confirmar o status de verdade (order=%s) -- ignorando este evento por ora",
                provider, result.provider_charge_id,
            )
            return {"matched": False, "unverified": True}
        effective_status = confirmed

    order = None
    if result.order_number:
        order = await db.scalar(select(Order).where(Order.number == result.order_number))
    if not order and result.provider_charge_id:
        pay = await db.scalar(
            select(Payment).where(Payment.provider_charge_id == result.provider_charge_id)
        )
        if pay:
            order = await db.get(Order, pay.order_id)
    if not order:
        evt.processed_at = datetime.now(UTC)
        return {"matched": False}

    payment = await db.scalar(
        select(Payment).where(Payment.order_id == order.id).order_by(Payment.created_at.desc())
    )
    if not payment:
        payment = Payment(
            order_id=order.id, provider=provider, method="pix",
            status="pending", amount_cents=order.grand_total_cents,
            provider_charge_id=result.provider_charge_id,
        )
        db.add(payment)
        await db.flush()

    if effective_status:
        payment.provider_payload_json = {**(payment.provider_payload_json or {}), "webhook": body}
        await _apply_status(
            db, order, payment, effective_status, source="webhook", background=background
        )

    evt.order_id = order.id
    evt.processed_at = datetime.now(UTC)
    await db.flush()
    await emit("payment.webhook_processed", {"order_id": str(order.id), "status": effective_status})
    return {"matched": True, "status": result.status}


async def get_status(db: AsyncSession, order_number: str) -> dict:
    order = await orders_service.get_by_number(db, order_number)
    payment = await db.scalar(
        select(Payment).where(Payment.order_id == order.id).order_by(Payment.created_at.desc())
    )
    return {
        "order_number": order.number,
        "order_status": order.status,
        "payment_status": order.payment_status,
        "method": payment.method if payment else None,
        "updated_at": payment.updated_at.isoformat() if payment and payment.updated_at else None,
    }


async def refund(
    db: AsyncSession, order_number: str, amount_cents: int | None,
    *, background: BackgroundTasks | None = None,
) -> dict:
    cfg = await load_config(db)
    order = await orders_service.get_by_number(db, order_number)
    payment = await db.scalar(
        select(Payment).where(Payment.order_id == order.id, Payment.status == "paid")
    )
    if not payment:
        raise ValidationError("Não há pagamento confirmado para reembolsar.")
    # reembolsa pelo provedor que processou ESSE pagamento (gravado na hora
    # da cobrança), não pelo "provedor ativo" atual -- podem ser diferentes
    # se o vínculo do método mudou depois.
    res = await _build_gateway(cfg, payment.provider).refund(payment=payment, amount_cents=amount_cents)
    if not res.ok:
        raise PaymentError(res.message or "Reembolso recusado pelo gateway.")
    payment.status = "refunded"
    order.payment_status = "refunded"
    if order.status not in ("refunded", "canceled"):
        try:
            await orders_service.transition(
                db, order, "refunded", actor_type="admin", message="Reembolso",
                background=background,
            )
        except ValidationError:
            order.status = "refunded"
    await db.flush()
    return {"ok": True, "provider_refund_id": res.provider_refund_id}


def charge_out(payment: Payment, order_number: str) -> dict:
    from app.modules.payment.codes import boleto_barcode_data_uri, pix_qr_data_uri

    return {
        "payment_id": str(payment.id),
        "order_number": order_number,
        "method": payment.method,
        "status": payment.status,
        "amount_cents": payment.amount_cents,
        "pix_qr_code": payment.pix_qr_code,
        "pix_qr_data_uri": pix_qr_data_uri(payment.pix_qr_code) if payment.pix_qr_code else None,
        "pix_expires_at": payment.pix_expires_at.isoformat() if payment.pix_expires_at else None,
        "boleto_url": payment.boleto_url,
        "boleto_barcode": payment.boleto_barcode,
        "boleto_barcode_data_uri": (
            boleto_barcode_data_uri(payment.boleto_barcode) if payment.boleto_barcode else None
        ),
    }
