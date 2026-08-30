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
    "order_processing": (
        "Pedido {{ number }} em separação",
        "<h2>Estamos preparando seu pedido 📦</h2>"
        "<p>O pedido <b>{{ number }}</b> entrou em separação e logo será enviado.</p>",
    ),
    "order_shipped": (
        "Seu pedido {{ number }} foi enviado",
        "<h2>Pedido a caminho 🚚</h2>"
        "<p>O pedido <b>{{ number }}</b> foi postado."
        "{% if tracking %} Código de rastreio: <b>{{ tracking }}</b>{% endif %}</p>"
        "{% if tracking_url %}<p><a href='{{ tracking_url }}'>Acompanhar entrega</a></p>{% endif %}",
    ),
    "order_in_transit": (
        "Pedido {{ number }} em trânsito",
        "<h2>Seu pedido está em trânsito 🛣️</h2>"
        "<p>O pedido <b>{{ number }}</b> está a caminho do endereço de entrega."
        "{% if tracking %} Rastreio: <b>{{ tracking }}</b>{% endif %}</p>"
        "{% if tracking_url %}<p><a href='{{ tracking_url }}'>Acompanhar entrega</a></p>{% endif %}",
    ),
    "order_delivered": (
        "Pedido {{ number }} entregue — conte como foi",
        "<h2>Entregue! 🎉</h2>"
        "<p>O pedido <b>{{ number }}</b> foi entregue. Esperamos que goste!</p>"
        "<p>Sua opinião ajuda muito outros clientes:</p>"
        "<p><a href='{{ review_url }}' "
        "style='display:inline-block;padding:12px 20px;background:#111;color:#fff;"
        "text-decoration:none;border-radius:8px'>Avaliar minha compra</a></p>",
    ),
    "order_canceled": (
        "Pedido {{ number }} cancelado",
        "<h2>Pedido cancelado</h2>"
        "<p>O pedido <b>{{ number }}</b> foi cancelado. "
        "Em caso de dúvida, entre em contato com a loja.</p>",
    ),
    "order_refunded": (
        "Reembolso do pedido {{ number }}",
        "<h2>Reembolso processado</h2>"
        "<p>O reembolso do pedido <b>{{ number }}</b> foi processado. "
        "O prazo de estorno depende do meio de pagamento.</p>",
    ),
    "cart_recovery": (
        "{{ subject }}",
        "<div>{{ body | e | replace('\n', '<br>'|safe) }}</div>"
        "<p style='margin-top:18px'><a href='{{ cta_url }}' class='btn'>Voltar para o meu carrinho</a></p>",
    ),
    "campaign": (
        "{{ subject }}",
        "<div>{{ body | e | replace('\n', '<br>'|safe) }}</div>"
        "{% if coupon %}<p style='margin-top:16px'>Use o cupom: "
        "<b style='font-size:18px;letter-spacing:1px'>{{ coupon }}</b></p>{% endif %}",
    ),
    "lead_coupon": (
        "Seu cupom chegou 🎁",
        "<h2>Obrigado por se cadastrar!</h2>"
        "<p>Use o cupom abaixo na sua primeira compra:</p>"
        "<p style='font-size:22px;font-weight:bold;letter-spacing:2px'>{{ coupon }}</p>",
    ),
    "account_created": (
        "Bem-vindo(a) à {{ store_name }}",
        "<h2>Conta criada 🎉</h2>"
        "<p>Sua conta na <b>{{ store_name }}</b> foi criada com sucesso.</p>"
        "<p>Use seu e-mail para entrar e acompanhar seus pedidos.</p>",
    ),
    "admin_order_created": (
        "[Loja] Novo pedido {{ number }} — R$ {{ '%.2f'|format(total_cents/100) }}",
        "<h2>Novo pedido: {{ number }}</h2>"
        "<p>Cliente: <b>{{ customer_name }}</b> ({{ email }})</p>"
        "<p>Total: <b>R$ {{ '%.2f'|format(total_cents/100) }}</b></p>"
        "<p>Itens:</p><ul>{% for it in items %}<li>{{ it }}</li>{% endfor %}</ul>"
        "<p><a href='{{ admin_url }}'>Abrir no painel</a></p>",
    ),
}


async def admin_notify_email(db: AsyncSession) -> str:
    """E-mail que recebe as notificações do lojista (só o aviso de novo pedido)."""
    conf = await _smtp_conf(db)
    return conf.get("from_email") or settings.admin_email or settings.smtp_from_email


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


_EMAIL_DEFAULTS = {
    "header_bg": "#111111", "header_fg": "#FFFFFF", "body_bg": "#FFFFFF",
    "text": "#111827", "btn_bg": "#111111", "btn_fg": "#FFFFFF", "footer": "",
}


async def _email_theme(db: AsyncSession) -> dict:
    try:
        from app.modules.theme.models import ThemeSettings

        row = await db.get(ThemeSettings, 1)
        if row:
            return {
                "header_bg": row.email_header_bg_color,
                "header_fg": row.email_header_text_color,
                "body_bg": row.email_body_bg_color,
                "text": row.email_text_color,
                "btn_bg": row.email_button_color,
                "btn_fg": row.email_button_text_color,
                "footer": row.email_footer_text or "",
            }
    except Exception:  # noqa: BLE001
        pass
    return dict(_EMAIL_DEFAULTS)


def _wrap_html(inner: str, subject: str, t: dict, store_name: str) -> str:
    """Molde visual do e-mail (cabeçalho colorido + corpo + rodapé)."""
    style_btn = (
        f"a[href],.btn{{background:{t['btn_bg']};color:{t['btn_fg']} !important;"
        "text-decoration:none;border-radius:8px;padding:12px 20px;display:inline-block}}"
    )
    footer = (
        f"<p style='margin:16px 0 0;font-size:12px;color:#9aa0a6'>{t['footer']}</p>"
        if t["footer"]
        else ""
    )
    return (
        f"<div style='margin:0;padding:24px;background:#f1f1f1;font-family:Arial,Helvetica,sans-serif'>"
        f"<div style='max-width:560px;margin:0 auto;background:{t['body_bg']};border-radius:12px;overflow:hidden'>"
        f"<div style='background:{t['header_bg']};color:{t['header_fg']};padding:18px 24px;font-weight:bold;font-size:16px'>{store_name}</div>"
        f"<div style='padding:24px;color:{t['text']};font-size:14px;line-height:1.55'>"
        f"<style>{style_btn}</style>{inner}{footer}</div>"
        f"</div></div>"
    )


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
    inner = _env.from_string(body_tpl).render(**context)
    conf = await _smtp_conf(db)
    et = await _email_theme(db)
    html = _wrap_html(inner, subject, et, conf["from_name"] or "Loja")

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
