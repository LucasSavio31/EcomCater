"""Envio de e-mail transacional via SMTP (config do banco sobrescreve o .env).

Registra cada envio em `email_log`. Usado pelos subscribers de eventos de pedido.
"""
from __future__ import annotations

import email.policy
import logging
import re
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage

import aiosmtplib
from jinja2 import Environment, select_autoescape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.admin.models import EmailLog, SmtpSettings

logger = logging.getLogger("mailer")

_env = Environment(autoescape=select_autoescape(["html", "xml"]))

# linha de status atual — vai em TODO e-mail de pedido
_STATUS_LINE = (
    "{% if status_label %}<p style='margin:12px 0;padding:10px 14px;background:#f4f4f5;"
    "border-radius:8px'>Status do pedido: <b>{{ status_label }}</b></p>{% endif %}"
)

# bloco reutilizável: itens + totais + pagamento + envio + endereço.
# auto-protegido: se o contexto não trouxer os dados, não renderiza nada.
_ORDER_DETAILS = (
    "{% if items is defined and items %}"
    "<table role='presentation' style='width:100%;border-collapse:collapse;margin:12px 0'>"
    "{% for it in items %}"
    "<tr>"
    "<td style='padding:6px 0;border-bottom:1px solid #eee'>{{ it.qty }}× {{ it.name }}"
    "{% if it.variant %} <span style='color:#888'>({{ it.variant }})</span>{% endif %}</td>"
    "<td style='padding:6px 0;border-bottom:1px solid #eee;text-align:right;white-space:nowrap'>"
    "R$ {{ '%.2f'|format(it.line_cents/100) }}</td>"
    "</tr>{% endfor %}"
    "<tr><td style='padding:6px 0'>Subtotal</td>"
    "<td style='padding:6px 0;text-align:right'>R$ {{ '%.2f'|format(items_total_cents/100) }}</td></tr>"
    "{% if discount_cents %}<tr><td style='padding:2px 0;color:#0a7d33'>Desconto"
    "{% if coupon_code %} ({{ coupon_code }}){% endif %}</td>"
    "<td style='padding:2px 0;text-align:right;color:#0a7d33'>- R$ {{ '%.2f'|format(discount_cents/100) }}</td></tr>{% endif %}"
    "<tr><td style='padding:2px 0'>Frete{% if shipping_method %} — {{ shipping_method }}{% endif %}</td>"
    "<td style='padding:2px 0;text-align:right'>R$ {{ '%.2f'|format(shipping_cents/100) }}</td></tr>"
    "<tr><td style='padding:8px 0;font-weight:bold;font-size:15px'>Total</td>"
    "<td style='padding:8px 0;text-align:right;font-weight:bold;font-size:15px'>R$ {{ '%.2f'|format(total_cents/100) }}</td></tr>"
    "</table>"
    "<p style='margin:10px 0 2px'><b>Pagamento:</b> {{ payment_method or '—' }}"
    "{% if installments and installments > 1 %} — {{ installments }}x{% endif %}</p>"
    "{% if pix_qr %}<p style='margin:6px 0'><b>Pix copia e cola:</b><br>"
    "<span style='word-break:break-all;font-family:monospace;font-size:12px'>{{ pix_qr }}</span></p>{% endif %}"
    "{% if boleto_url %}<p style='margin:6px 0'><a href='{{ boleto_url }}'>Abrir boleto</a></p>{% endif %}"
    "<p style='margin:10px 0 2px'><b>Envio:</b> {{ shipping_method or '—' }}"
    "{% if shipping_eta %} — prazo estimado {{ shipping_eta }} dia(s){% endif %}</p>"
    "{% if tracking_code %}<p style='margin:2px 0'><b>Rastreio:</b> {{ tracking_code }}</p>{% endif %}"
    "{% if address %}<p style='margin:10px 0 2px'><b>Entrega em:</b><br>"
    "{{ address.recipient }}<br>{{ address.line }}"
    "{% if address.district %} — {{ address.district }}{% endif %}<br>"
    "{{ address.city }}/{{ address.state }} — CEP {{ address.zip }}</p>"
    "{% endif %}"
    "{% endif %}"  # fecha o "{% if items is defined and items %}"
)


def _order_email(intro: str, cta: str = "") -> str:
    """intro + status atual + resumo do pedido/envio + call-to-action opcional."""
    return intro + _STATUS_LINE + _ORDER_DETAILS + cta


_TRACK_CTA = (
    "{% if tracking_url %}<p style='margin:12px 0'>"
    "<a href='{{ tracking_url }}' class='btn' style='{{ btn_style }}'>Acompanhar entrega</a></p>{% endif %}"
)

TEMPLATES: dict[str, tuple[str, str]] = {
    "order_created": (
        "Pedido {{ number }} recebido",
        _order_email(
            "<h2>Recebemos seu pedido {{ number }}</h2>"
            "<p>Olá! Seu pedido foi registrado e está <b>aguardando pagamento</b>.</p>"
        ),
    ),
    "payment_confirmed": (
        "Pagamento confirmado — pedido {{ number }}",
        _order_email(
            "<h2>Pagamento aprovado! ✅</h2>"
            "<p>O pagamento do pedido <b>{{ number }}</b> foi confirmado e já estamos "
            "preparando o envio.</p>"
        ),
    ),
    "payment_failed": (
        "Pagamento não concluído — pedido {{ number }}",
        _order_email(
            "<h2>Não conseguimos confirmar seu pagamento</h2>"
            "<p>O pagamento do pedido <b>{{ number }}</b> não foi concluído. "
            "Você pode tentar novamente.</p>"
        ),
    ),
    "order_processing": (
        "Pedido {{ number }} em separação",
        _order_email(
            "<h2>Estamos preparando seu pedido 📦</h2>"
            "<p>O pedido <b>{{ number }}</b> entrou em separação e logo será enviado.</p>"
        ),
    ),
    "order_tracking_available": (
        "Pedido {{ number }}: código de rastreio disponível",
        _order_email(
            "<h2>Seu rastreio já está disponível 🔎</h2>"
            "<p>A etiqueta do pedido <b>{{ number }}</b> foi emitida e o código de "
            "rastreio já está disponível."
            "{% if tracking %} Código: <b>{{ tracking }}</b>{% endif %}</p>"
            "<p>Assim que o objeto for postado nos Correios você recebe um novo aviso.</p>",
            _TRACK_CTA,
        ),
    ),
    "order_shipped": (
        "Seu pedido {{ number }} foi enviado",
        _order_email(
            "<h2>Pedido a caminho 🚚</h2>"
            "<p>O pedido <b>{{ number }}</b> foi postado."
            "{% if tracking %} Código de rastreio: <b>{{ tracking }}</b>{% endif %}</p>",
            _TRACK_CTA,
        ),
    ),
    "order_in_transit": (
        "Pedido {{ number }} em trânsito",
        _order_email(
            "<h2>Seu pedido está em trânsito 🛣️</h2>"
            "<p>O pedido <b>{{ number }}</b> está a caminho do endereço de entrega."
            "{% if tracking %} Rastreio: <b>{{ tracking }}</b>{% endif %}</p>",
            _TRACK_CTA,
        ),
    ),
    "order_delivered": (
        "Pedido {{ number }} entregue — conte como foi",
        _order_email(
            "<h2>Entregue! 🎉</h2>"
            "<p>O pedido <b>{{ number }}</b> foi entregue. Esperamos que goste!</p>",
            "<p style='margin:12px 0'><a href='{{ review_url }}' class='btn' style='{{ btn_style }}'>Avaliar minha compra</a></p>",
        ),
    ),
    "order_canceled": (
        "Pedido {{ number }} cancelado",
        _order_email(
            "<h2>Pedido cancelado</h2>"
            "<p>O pedido <b>{{ number }}</b> foi cancelado. "
            "Em caso de dúvida, entre em contato com a loja.</p>"
        ),
    ),
    "order_refunded": (
        "Reembolso do pedido {{ number }}",
        _order_email(
            "<h2>Reembolso processado</h2>"
            "<p>O reembolso do pedido <b>{{ number }}</b> foi processado. "
            "O prazo de estorno depende do meio de pagamento.</p>"
        ),
    ),
    "cart_recovery": (
        "{{ subject }}",
        "<h2 style='margin:0 0 12px;font-size:18px;text-transform:uppercase;letter-spacing:.5px'>{{ subject }}</h2>"
        "<div>{{ body | e | replace('\n', '<br>'|safe) }}</div>"
        "{% if items %}"
        "<table role='presentation' style='width:100%;border-collapse:collapse;margin:16px 0'>"
        "{% for it in items %}<tr>"
        "<td style='padding:8px 0;border-bottom:1px solid #eee'>{{ it.qty }}× {{ it.name }}"
        "{% if it.variant %}<br><span style='color:#888;font-size:12px'>{{ it.variant }}</span>{% endif %}</td>"
        "<td style='padding:8px 0;border-bottom:1px solid #eee;text-align:right;white-space:nowrap'>"
        "R$ {{ '%.2f'|format(it.line_cents/100) }}</td>"
        "</tr>{% endfor %}"
        "<tr><td style='padding:10px 0;font-weight:bold;font-size:15px'>Total</td>"
        "<td style='padding:10px 0;text-align:right;font-weight:bold;font-size:15px'>"
        "R$ {{ '%.2f'|format((total_cents or 0)/100) }}</td></tr>"
        "</table>{% endif %}"
        "<p style='margin-top:18px'><a href='{{ cta_url }}' class='btn' style='{{ btn_style }}'>Voltar para o meu carrinho</a></p>",
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
        "<p>Use seu e-mail e a senha que você escolheu para entrar e acompanhar seus pedidos.</p>",
    ),
    "password_reset": (
        "Redefinição de senha — {{ store_name }}",
        "<h2>Redefinir sua senha</h2>"
        "<p>Recebemos um pedido para redefinir a senha da conta <b>{{ email }}</b>"
        "{% if is_admin %} (painel administrativo){% endif %}.</p>"
        "<p style='margin:14px 0'><a href='{{ reset_url }}' class='btn' style='{{ btn_style }}'>Criar nova senha</a></p>"
        "<p style='font-size:12px;color:#9aa0a6'>O link vale por {{ ttl_min }} minutos e só "
        "pode ser usado uma vez. Se não foi você, ignore este e-mail — nada muda.</p>",
    ),
    "account_access": (
        "Sua conta na {{ store_name }} — dados de acesso",
        "<h2>Sua conta está pronta ✅</h2>"
        "<p>Criamos uma conta para você acompanhar as compras na <b>{{ store_name }}</b>.</p>"
        "<p><b>Dados de acesso:</b></p>"
        "<p style='margin:4px 0'>Login (e-mail): <b>{{ email }}</b></p>"
        "<p style='margin:4px 0'>Senha: <b>seu CPF</b> (só números{% if cpf_masked %}, ex.: {{ cpf_masked }}{% endif %})</p>"
        "<p style='margin:12px 0'><a href='{{ login_url }}' class='btn' style='{{ btn_style }}'>Acessar minha conta</a></p>"
        "<p style='font-size:12px;color:#9aa0a6'>Recomendamos trocar a senha depois do primeiro acesso, em Minha conta.</p>",
    ),
    "admin_order_created": (
        "[Loja] Novo pedido {{ number }} — R$ {{ '%.2f'|format(total_cents/100) }}",
        _order_email(
            "<h2>Novo pedido: {{ number }}</h2>"
            "<p>Cliente: <b>{{ customer_name }}</b> ({{ email }})"
            "{% if customer_phone %} — {{ customer_phone }}{% endif %}</p>",
            "<p style='margin-top:14px'><a href='{{ admin_url }}' class='btn' style='{{ btn_style }}'>Abrir no painel</a></p>",
        ),
    ),
    "admin_order_error": (
        "[Loja] Falha ao finalizar o pedido {{ number }}",
        "<h2 style='color:#b00020'>Erro na finalização do pedido {{ number }}</h2>"
        "<p>O pedido foi criado normalmente, mas alguns passos pós-pedido falharam "
        "e ficaram registrados no pedido:</p>"
        "<ul>{{ failures_html | safe }}</ul>"
        "<p style='margin-top:14px'><a href='{{ admin_url }}' class='btn' style='{{ btn_style }}'>Abrir no painel</a></p>",
    ),
    "backup_result": (
        "[Loja] Backup {{ 'OK' if ok else 'FALHOU' }} — {{ when }}",
        "<h2>{{ '✅ Backup concluído' if ok else '❌ Backup falhou' }}</h2>"
        "<p>Disparo: <b>{{ trigger }}</b> — {{ when }}</p>"
        "{% if ok %}<p>Arquivo: <b>{{ filename }}</b> ({{ size_mb }} MB)"
        "{% if with_media %} — inclui mídia{% endif %}</p>"
        "{% if destinations %}<p>Cópias: {{ destinations }}</p>{% endif %}"
        "{% else %}<p style='color:#b00020'>Erro: {{ error }}</p>"
        "<p>Verifique o menu Sistema → Backup no painel.</p>{% endif %}",
    ),
    "health_alert": (
        "[Loja] {{ '⚠️' if bad else '✅' }} {{ service_label }} — {{ status_pt }}",
        "<h2>{{ '⚠️ Serviço com problema' if bad else '✅ Serviço normalizado' }}</h2>"
        "<p><b>{{ service_label }}</b>: {{ status_pt }}</p>"
        "<p>{{ detail }}</p>"
        "<p style='font-size:12px;color:#9aa0a6'>Verificado em {{ when }}. "
        "Painel: Sistema → Infraestrutura.</p>",
    ),
    "daily_digest": (
        "[Loja] Resumo do dia — {{ date }}",
        "<h2>Resumo do dia — {{ date }}</h2>"
        "<table role='presentation' style='width:100%;border-collapse:collapse;margin:12px 0'>"
        "<tr><td style='padding:6px 0;border-bottom:1px solid #eee'>Pedidos criados</td>"
        "<td style='padding:6px 0;border-bottom:1px solid #eee;text-align:right'><b>{{ orders }}</b></td></tr>"
        "<tr><td style='padding:6px 0;border-bottom:1px solid #eee'>Pedidos pagos</td>"
        "<td style='padding:6px 0;border-bottom:1px solid #eee;text-align:right'><b>{{ paid }}</b></td></tr>"
        "<tr><td style='padding:6px 0;border-bottom:1px solid #eee'>Aguardando pagamento</td>"
        "<td style='padding:6px 0;border-bottom:1px solid #eee;text-align:right'><b>{{ pending }}</b></td></tr>"
        "<tr><td style='padding:8px 0'>Faturado (pago) no dia</td>"
        "<td style='padding:8px 0;text-align:right;font-weight:bold;font-size:15px'>R$ {{ '%.2f'|format(revenue_cents/100) }}</td></tr>"
        "</table>"
        "<h3 style='margin:14px 0 6px;font-size:14px'>Status do sistema</h3>"
        "<ul style='margin:0;padding-left:18px'>"
        "{% for s in services %}<li>{{ s.label }}: <b>{{ s.status_pt }}</b>"
        "{% if s.detail %} <span style='color:#888'>({{ s.detail }})</span>{% endif %}</li>{% endfor %}"
        "</ul>"
        "<p style='margin-top:10px'>Último backup: {{ last_backup or 'nenhum registrado' }}</p>",
    ),
}

# rótulos pt-BR para status de saúde
STATUS_PT = {"ok": "operacional", "degraded": "instável", "down": "fora do ar"}


async def admin_notify_email(db: AsyncSession) -> str:
    """E-mail que recebe os alertas do lojista (novo pedido, anomalia de saúde).

    Preferência: a conta de administrador (super admin) → qualquer admin ativo
    → remetente do SMTP → ADMIN_EMAIL do .env.
    """
    from app.modules.admin.models import AdminUser

    admin = await db.scalar(
        select(AdminUser)
        .where(AdminUser.is_active.is_(True))
        .order_by((AdminUser.role == "super_admin").desc(), AdminUser.created_at.asc())
        .limit(1)
    )
    if admin and admin.email:
        return admin.email
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
            "use_ssl": row.use_ssl,
            "from_email": row.from_email or settings.smtp_from_email,
            "from_name": row.from_name or settings.smtp_from_name,
        }
    return {
        "host": settings.smtp_host,
        "port": settings.smtp_port,
        "username": settings.smtp_user or None,
        "password": settings.smtp_password or None,
        "use_tls": settings.smtp_use_tls,
        "use_ssl": False,
        "from_email": settings.smtp_from_email,
        "from_name": settings.smtp_from_name,
    }


_EMAIL_DEFAULTS = {
    "header_bg": "#111111", "header_fg": "#FFFFFF", "body_bg": "#FFFFFF",
    "text": "#111827", "btn_bg": "#111111", "btn_fg": "#FFFFFF", "footer": "",
}


async def _email_theme(db: AsyncSession) -> dict:
    out = dict(_EMAIL_DEFAULTS)
    out["logo_url"] = None
    out["logo_key"] = None
    out["store_name"] = None
    try:
        from app.modules.admin.models import StoreSettings
        from app.modules.theme.models import ThemeSettings
        from app.shared.storage import storage

        row = await db.get(ThemeSettings, 1)
        if row:
            out.update(
                header_bg=row.email_header_bg_color,
                header_fg=row.email_header_text_color,
                body_bg=row.email_body_bg_color,
                text=row.email_text_color,
                btn_bg=row.email_button_color,
                btn_fg=row.email_button_text_color,
                footer=row.email_footer_text or "",
            )
            if row.logo_key:
                out["logo_url"] = storage.url(row.logo_key)
                out["logo_key"] = row.logo_key
        store = await db.get(StoreSettings, 1)
        if store and store.store_name:
            out["store_name"] = store.store_name
    except Exception:  # noqa: BLE001
        pass
    return out


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t\r\f\v]+")


def _html_to_text(html: str) -> str:
    txt = html.replace("</p>", "\n").replace("<br>", "\n").replace("<br/>", "\n")
    txt = _TAG_RE.sub("", txt)
    txt = _WS_RE.sub(" ", txt)
    lines = [ln.strip() for ln in txt.splitlines()]
    return "\n".join(ln for ln in lines if ln).strip()


def _btn_style(t: dict) -> str:
    """Estilo INLINE do botão (o Gmail descarta blocos <style>, então o botão
    real vem de `style=` no próprio <a>)."""
    return (
        f"background:{t.get('btn_bg', '#111111')};color:{t.get('btn_fg', '#FFFFFF')};"
        "text-decoration:none;border-radius:8px;padding:13px 24px;display:inline-block;"
        "font-weight:bold;font-family:Arial,Helvetica,sans-serif;font-size:14px"
    )


def _wrap_html(inner: str, subject: str, t: dict, store_name: str) -> str:
    """Molde visual do e-mail (cabeçalho com logo/nome da loja + corpo + rodapé)."""
    name = t.get("store_name") or store_name
    style_btn = (
        f".btn{{{_btn_style(t)}}} a.btn{{color:{t.get('btn_fg', '#FFFFFF')} !important}}"
    )
    footer = (
        f"<p style='margin:16px 0 0;font-size:12px;color:#9aa0a6'>{t['footer']}</p>"
        if t["footer"]
        else ""
    )
    # logo embutido como anexo inline (cid:) — e-mail funciona mesmo sem URL
    # pública válida; cai para texto se não houver logo.
    if t.get("logo_cid"):
        header_inner = (
            f"<img src='cid:{t['logo_cid']}' alt='{name}' "
            "style='max-height:40px;vertical-align:middle'>"
        )
    elif t.get("logo_url"):
        header_inner = (
            f"<img src='{t['logo_url']}' alt='{name}' "
            "style='max-height:40px;vertical-align:middle'>"
        )
    else:
        header_inner = name
    return (
        f"<div style='margin:0;padding:24px;background:#f1f1f1;font-family:Arial,Helvetica,sans-serif'>"
        f"<div style='max-width:560px;margin:0 auto;background:{t['body_bg']};border-radius:12px;overflow:hidden'>"
        f"<div style='background:{t['header_bg']};color:{t['header_fg']};padding:16px 24px;font-weight:bold;font-size:16px'>{header_inner}</div>"
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
    attachments: list[tuple[str, bytes, str, str]] | None = None,
) -> bool:
    """`attachments`: lista de (filename, data, maintype, subtype), ex.:
    ("fatura.pdf", b"...", "application", "pdf")."""
    conf = await _smtp_conf(db)
    et = await _email_theme(db)

    subj_tpl, body_tpl = TEMPLATES.get(template, ("Notificação", "<p>{{ message|default('') }}</p>"))
    ctx = {"btn_style": _btn_style(et), **context}
    subject = _env.from_string(subj_tpl).render(**ctx)
    inner = _env.from_string(body_tpl).render(**ctx)

    # tenta embutir o logo como imagem inline (cid:)
    logo_bytes: bytes | None = None
    if et.get("logo_key"):
        try:
            from app.shared.storage import storage

            logo_bytes = storage.read(et["logo_key"])
            et["logo_cid"] = "storelogo"
        except Exception:  # noqa: BLE001
            logo_bytes = None

    html = _wrap_html(inner, subject, et, conf["from_name"] or "Loja")

    # nome do remetente = NOME DA LOJA (StoreSettings). Muda sozinho quando a
    # loja é renomeada; cai para o from_name do SMTP e depois "Loja".
    from_name = et.get("store_name") or conf["from_name"] or "Loja"

    msg = EmailMessage()
    msg["From"] = f"{from_name} <{conf['from_email']}>"
    msg["To"] = to
    msg["Subject"] = subject
    # fallback texto puro = versão sem tags do corpo (é o que o Gmail mostra na
    # prévia da lista; nunca "este e-mail requer HTML").
    msg.set_content(_html_to_text(inner) or subject)
    msg.add_alternative(html, subtype="html")
    if logo_bytes:
        sub = "png" if logo_bytes[:8].startswith(b"\x89PNG") else "webp" if logo_bytes[:4] == b"RIFF" else "jpeg"
        msg.get_payload()[1].add_related(logo_bytes, maintype="image", subtype=sub, cid="storelogo")
    for fname, data, maintype, subtype in attachments or []:
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=fname)

    status, error = "sent", None
    now = datetime.now(UTC)
    if settings.api_env == "test":
        # não abre conexão SMTP real na suíte; só registra o EmailLog
        pass
    else:
        error = await _smtp_send(conf, msg)
        if error:
            # SMTP fora do ar / recusou: NÃO propaga — a mensagem entra na fila
            # e um agendador tenta de novo. Nunca trava quem chamou (checkout).
            status = "queued"
            logger.warning("e-mail '%s' p/ %s enfileirado (SMTP: %s)", template, to, error)

    db.add(
        EmailLog(
            to_email=to,
            template=template,
            subject=subject,
            status=status,
            error=error,
            order_id=order_id,
            created_at=now,
            sent_at=now if status == "sent" else None,
            attempts=1 if status != "sent" else 0,
            next_attempt_at=(now + timedelta(seconds=90)) if status == "queued" else None,
            raw_message=msg.as_bytes() if status == "queued" else None,
        )
    )
    return status in ("sent", "queued")


async def _smtp_send(conf: dict, msg: EmailMessage) -> str | None:
    """Envia via SMTP. Devolve None em sucesso ou a mensagem de erro (curta)."""
    # porta 465 = TLS implícito (use_ssl); 587 = STARTTLS (use_tls).
    # aiosmtplib recusa os dois juntos, então escolhe um.
    if conf.get("use_ssl") or conf["port"] == 465:
        tls_kwargs = {"use_tls": True}
    else:
        tls_kwargs = {"start_tls": bool(conf["use_tls"])}
    try:
        await aiosmtplib.send(
            msg,
            hostname=conf["host"],
            port=conf["port"],
            username=conf["username"] or None,
            password=conf["password"] or None,
            timeout=10,
            **tls_kwargs,
        )
        return None
    except Exception as exc:  # noqa: BLE001
        return str(exc)[:400]


async def retry_queued(db: AsyncSession, limit: int = 25) -> dict:
    """Reprocessa a fila de e-mails (status='queued' e prazo vencido). Chamada
    pelo agendador `email_retry`. Backoff exponencial até 1h; desiste após 8
    tentativas (status='failed')."""
    now = datetime.now(UTC)
    rows = list(
        await db.scalars(
            select(EmailLog)
            .where(
                EmailLog.status == "queued",
                (EmailLog.next_attempt_at.is_(None)) | (EmailLog.next_attempt_at <= now),
            )
            .order_by(EmailLog.created_at)
            .limit(limit)
        )
    )
    if not rows:
        return {"sent": 0, "still_queued": 0, "failed": 0}

    conf = await _smtp_conf(db)
    sent = failed = 0
    for row in rows:
        if not row.raw_message:
            row.status, row.error = "failed", "sem corpo para reenviar"
            failed += 1
            continue
        try:
            msg = email.message_from_bytes(row.raw_message, policy=email.policy.default)
        except Exception as exc:  # noqa: BLE001
            row.status, row.error = "failed", f"corpo inválido: {exc}"[:400]
            failed += 1
            continue
        err = await _smtp_send(conf, msg)  # type: ignore[arg-type]
        row.attempts = (row.attempts or 0) + 1
        if err is None:
            row.status, row.error, row.sent_at = "sent", None, now
            row.next_attempt_at = None
            sent += 1
        elif row.attempts >= 8:
            row.status, row.error = "failed", err
            failed += 1
        else:
            row.error = err
            row.next_attempt_at = now + timedelta(
                seconds=min(3600, 60 * (2 ** (row.attempts - 1)))
            )
    await db.commit()
    still = sum(1 for r in rows if r.status == "queued")
    if sent or failed:
        logger.info("fila de e-mail: %s enviados, %s desistidos, %s pendentes", sent, failed, still)
    return {"sent": sent, "still_queued": still, "failed": failed}


async def send_test(db: AsyncSession, to: str) -> dict:
    """Envia o e-mail de teste e devolve {ok, error} — o `error` traz a
    mensagem real do servidor SMTP (ex.: '535 BadCredentials') pra aparecer
    no painel."""
    await send(db, to=to, template="__test__", context={"message": "Teste de SMTP OK."})
    await db.flush()
    row = await db.scalar(
        select(EmailLog)
        .where(EmailLog.template == "__test__", EmailLog.to_email == to)
        .order_by(EmailLog.created_at.desc())
        .limit(1)
    )
    if row and row.status == "sent":
        return {"ok": True, "error": None}
    return {"ok": False, "error": (row.error if row and row.error else "Falha ao enviar (sem detalhe).")}
