"""Envio de e-mail transacional via SMTP (config do banco sobrescreve o .env).

Registra cada envio em `email_log`. Usado pelos subscribers de eventos de pedido.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from email.message import EmailMessage

import aiosmtplib
from jinja2 import Environment, select_autoescape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.admin.models import EmailLog, SmtpSettings

logger = logging.getLogger("mailer")

_env = Environment(autoescape=select_autoescape(["html", "xml"]))

TEMPLATES: dict[str, tuple[str, str]] = {
    "order_created": (
        "Pedido {{ number }} recebido",
        "<h2>Recebemos seu pedido {{ number }}</h2>"
        "<p>Olá! Seu pedido foi registrado e está <b>aguardando pagamento</b>.</p>"
        "<p>Total: <b>R$ {{ '%.2f'|format(total_cents/100) }}</b></p>"
        "{% if pix_qr %}<p><b>Pix copia e cola:</b><br><code>{{ pix_qr }}</code></p>{% endif %}"
        "{% if boleto_url %}<p><a href='{{ boleto_url }}'>Abrir boleto</a></p>{% endif %}",
    ),
    "payment_confirmed": (
        "Pagamento confirmado — pedido {{ number }}",
        "<h2>Pagamento aprovado!</h2>"
        "<p>O pagamento do pedido <b>{{ number }}</b> foi confirmado e já estamos "
        "preparando o envio.</p>",
    ),
    "payment_failed": (
        "Pagamento não concluído — pedido {{ number }}",
        "<h2>Não conseguimos confirmar seu pagamento</h2>"
        "<p>O pagamento do pedido <b>{{ number }}</b> não foi concluído. "
        "Você pode tentar novamente.</p>",
    ),
    "order_shipped": (
        "Seu pedido {{ number }} foi enviado",
        "<h2>Pedido a caminho 🚚</h2>"
        "<p>O pedido <b>{{ number }}</b> foi postado."
        "{% if tracking %} Código de rastreio: <b>{{ tracking }}</b>{% endif %}</p>",
    ),
    "order_delivered": (
        "Pedido {{ number }} entregue",
        "<h2>Entregue! 🎉</h2><p>O pedido <b>{{ number }}</b> foi entregue. Aproveite!</p>",
    ),
}


async def _smtp_conf(db: AsyncSession) -> dict:
    row = await db.get(SmtpSettings, 1)
    if row and row.host:
        return {
            "host": row.host,
            "port": row.port or 587,
            "username": row.username,
            "password": row.password_enc,
            "use_tls": row.use_tls,
            "from_email": row.from_email or settings.smtp_from_email,
            "from_name": row.from_name or settings.smtp_from_name,
        }
    return {
        "host": settings.smtp_host,
        "port": settings.smtp_port,
        "username": settings.smtp_user or None,
        "password": settings.smtp_password or None,
        "use_tls": settings.smtp_use_tls,
        "from_email": settings.smtp_from_email,
        "from_name": settings.smtp_from_name,
    }


async def send(
    db: AsyncSession,
    *,
    to: str,
    template: str,
    context: dict,
    order_id: str | None = None,
) -> bool:
    subj_tpl, body_tpl = TEMPLATES.get(template, ("Notificação", "<p>{{ message|default('') }}</p>"))
    subject = _env.from_string(subj_tpl).render(**context)
    html = _env.from_string(body_tpl).render(**context)
    conf = await _smtp_conf(db)

    msg = EmailMessage()
    msg["From"] = f"{conf['from_name']} <{conf['from_email']}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content("Este e-mail requer um cliente compatível com HTML.")
    msg.add_alternative(html, subtype="html")

    status, error = "sent", None
    try:
        await aiosmtplib.send(
            msg,
            hostname=conf["host"],
            port=conf["port"],
            username=conf["username"] or None,
            password=conf["password"] or None,
            start_tls=bool(conf["use_tls"]),
            timeout=15,
        )
    except Exception as exc:  # noqa: BLE001
        status, error = "failed", str(exc)[:400]
        logger.warning("falha ao enviar e-mail '%s' para %s: %s", template, to, error)

    db.add(
        EmailLog(
            to_email=to,
            template=template,
            subject=subject,
            status=status,
            error=error,
            order_id=order_id,
            created_at=datetime.now(UTC),
        )
    )
    return status == "sent"


async def send_test(db: AsyncSession, to: str) -> bool:
    return await send(db, to=to, template="__test__", context={"message": "Teste de SMTP OK."})
