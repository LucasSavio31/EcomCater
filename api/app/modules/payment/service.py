"""Regra de negócio do módulo `payment` — cobrança, webhook idempotente,
reconciliação do pedido e reembolso."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import DomainError, NotFoundError, PaymentError, ValidationError
from app.core.events import emit
from app.modules.orders import service as orders_service
from app.modules.orders.models import Order
from app.modules.payment.config import PaymentConfig
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


async def load_config(db: AsyncSession) -> PaymentConfig:
    from app.modules.admin.models import ModuleRow

    row = await db.get(ModuleRow, "payment")
    raw = dict(row.config_json) if row and row.config_json else {}
    return PaymentConfig(**raw)


async def save_config(db: AsyncSession, patch: dict) -> PaymentConfig:
    from app.modules.admin.models import ModuleRow

    row = await db.get(ModuleRow, "payment")
    current = dict(row.config_json) if row and row.config_json else {}
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


def _gateway(cfg: PaymentConfig) -> PaymentGateway:
    if cfg.active_provider == "fake":
        return FakeGateway()
    if cfg.active_provider == "appmax":
        base = settings.appmax_api_url
        if not cfg.appmax_sandbox:
            base = base.replace("homolog.sandboxappmax.com.br", "admin.appmax.com.br")
        return AppmaxGateway(
            access_token=cfg.appmax_access_token or settings.appmax_access_token,
            base_url=base,
            webhook_secret=cfg.appmax_webhook_secret or settings.appmax_webhook_secret,
        )
    raise DomainError(f"Provedor de pagamento desconhecido: {cfg.active_provider}")


async def create_charge(db: AsyncSession, *, order_number: str, method: str, card: dict | None) -> Payment:
    cfg = await load_config(db)
    if method not in ("credit_card", "pix", "boleto"):
        raise ValidationError("Método de pagamento inválido.")
    if not getattr(cfg.methods, method, False):
        raise ValidationError(f"Método '{method}' não está habilitado.")

    order = await orders_service.get_by_number(db, order_number)
    if order.status not in ("pending_payment",):
        raise ValidationError("Este pedido não está aguardando pagamento.")

    existing = await db.scalar(
        select(Payment).where(Payment.order_id == order.id, Payment.status.in_(("pending", "authorized", "paid")))
    )
    if existing and existing.status == "paid":
        return existing

    gateway = _gateway(cfg)
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

    await _apply_status(db, order, payment, charge.status, source="charge")
    return payment


def _parse_dt(v: str | None):
    if not v:
        return None
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None


async def _apply_status(db: AsyncSession, order: Order, payment: Payment, normalized: str, *, source: str) -> None:
    action = _ORDER_ACTION.get(normalized)
    if normalized == "paid":
        if payment.status == "paid" and order.payment_status == "paid":
            return  # idempotente: cobrança instantânea + webhook não devem duplicar
        payment.status = "paid"
        if not payment.paid_at:
            payment.paid_at = datetime.now(UTC)
        order.payment_status = "paid"
        await orders_service.finalize_paid(db, await orders_service._load(db, order.id))
    elif action == "cancel":
        payment.status = "failed"
        if order.status == "pending_payment":
            await orders_service.transition(db, order, "canceled", actor_type="system", message=f"Pagamento não concluído ({source})")
    elif action == "refund":
        payment.status = "refunded" if normalized == "refunded" else "chargeback"
        order.payment_status = payment.status
        if order.status not in ("refunded", "canceled"):
            try:
                await orders_service.transition(db, order, "refunded", actor_type="system", message=f"{normalized} ({source})")
            except ValidationError:
                order.status = "refunded"
    await db.flush()


async def handle_webhook(db: AsyncSession, provider: str, headers: dict, raw_body: bytes, body: dict) -> dict:
    cfg = await load_config(db)
    gateway = _gateway(cfg)
    if gateway.slug != provider and provider not in _PROVIDERS:
        raise NotFoundError("Provedor de webhook desconhecido.")

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
    evt.signature_valid = signature_valid
    evt.payload_json = body
    await db.flush()

    if not signature_valid:
        logger.warning("webhook %s com assinatura inválida", provider)
        raise PaymentError("Assinatura de webhook inválida.", code="bad_signature")

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

    if result.status:
        payment.provider_payload_json = {**(payment.provider_payload_json or {}), "webhook": body}
        await _apply_status(db, order, payment, result.status, source="webhook")

    evt.order_id = order.id
    evt.processed_at = datetime.now(UTC)
    await db.flush()
    await emit("payment.webhook_processed", {"order_id": str(order.id), "status": result.status})
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


async def refund(db: AsyncSession, order_number: str, amount_cents: int | None) -> dict:
    cfg = await load_config(db)
    order = await orders_service.get_by_number(db, order_number)
    payment = await db.scalar(
        select(Payment).where(Payment.order_id == order.id, Payment.status == "paid")
    )
    if not payment:
        raise ValidationError("Não há pagamento confirmado para reembolsar.")
    res = await _gateway(cfg).refund(payment=payment, amount_cents=amount_cents)
    if not res.ok:
        raise PaymentError(res.message or "Reembolso recusado pelo gateway.")
    payment.status = "refunded"
    order.payment_status = "refunded"
    if order.status not in ("refunded", "canceled"):
        try:
            await orders_service.transition(db, order, "refunded", actor_type="admin", message="Reembolso")
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
