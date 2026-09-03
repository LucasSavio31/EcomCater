"""Fatura do pedido em PDF — MESMO layout da fatura do painel (DFAT-e).

Reproduz o HTML/CSS de `admin/.../pedidos/fatura/page.tsx` num template
server-side e converte com WeasyPrint (HTML+CSS -> PDF, sem browser).
Usada como anexo do e-mail de pagamento confirmado.
"""
from __future__ import annotations

from datetime import UTC, datetime

from jinja2 import Environment, select_autoescape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.orders.models import Order
from app.shared.timez import store_tz

_PAYMENT_STATUS_PT = {
    "pending": "Aguardando", "paid": "Pago", "failed": "Falhou",
    "refunded": "Estornado", "canceled": "Cancelado",
}
_ENVIO_LABEL = {
    "delivered": "Recebido", "shipped": "Enviado",
    "canceled": "Cancelado", "refunded": "Estornado",
}

_env = Environment(autoescape=select_autoescape(["html", "xml"]))


def _money(cents: int | None) -> str:
    s = f"{(cents or 0) / 100:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _mask_doc(raw: str | None) -> str:
    d = "".join(ch for ch in (raw or "") if ch.isdigit())
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    return raw or "—"


def _addr_line(a: dict | None) -> str:
    a = a or {}
    base = f"{a.get('street', '')}, {a.get('number', '')}".strip(", ")
    if a.get("complement"):
        base += f" — {a['complement']}"
    return base or "—"


def _fmt_dt(dt: datetime | None) -> str:
    if not dt:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(store_tz()).strftime("%d/%m/%Y, %H:%M")


_TEMPLATE = _env.from_string(
    """<!doctype html><html><head><meta charset="utf-8"><style>
@page { size: A4; margin: 10mm; }
#fat { font-family: "Liberation Sans", Arial, Helvetica, sans-serif; color:#000; font-size:11px; line-height:1.35; }
.box { border:1px solid #000; }
.row { display:flex; }
.cell { border-right:1px solid #000; padding:3px 6px; flex:1; }
.cell:last-child { border-right:0; }
.lbl { font-size:8px; text-transform:uppercase; letter-spacing:.3px; }
.val { font-size:11px; }
.sec { border:1px solid #000; border-top:0; }
.sec-h { background:#eee; font-weight:bold; font-size:9px; text-transform:uppercase; padding:2px 6px; border-bottom:1px solid #000; }
table { width:100%; border-collapse:collapse; }
th, td { border:1px solid #000; padding:3px 5px; text-align:left; vertical-align:top; }
th { background:#eee; font-size:8px; text-transform:uppercase; }
.r { text-align:right; } .c { text-align:center; } .mt { margin-top:6px; }
</style></head><body><div id="fat">

  <div class="box">
    <div class="cell" style="border-right:0">
      <div class="val">Recebemos de <b>{{ loja_nome }}</b> os produtos constantes da fatura indicada ao lado.</div>
      <div class="row mt" style="border-top:1px solid #000">
        <div class="cell"><div class="lbl">Data do recebimento</div><div class="val">&nbsp;</div></div>
        <div class="cell" style="flex:2"><div class="lbl">Identificação e assinatura do recebedor</div><div class="val">&nbsp;</div></div>
        <div class="cell c" style="flex:0 0 150px;display:flex;flex-direction:column;justify-content:center">
          <div style="font-weight:bold;font-size:13px">FATURA</div><div class="val">Nº {{ order.number }}</div>
        </div>
      </div>
    </div>
  </div>

  <div class="row box mt">
    <div class="cell" style="flex:2">
      <div style="font-weight:bold;font-size:12px">{{ loja_nome }}</div>
      <div class="val">{{ addr_loja }}</div>
      <div class="val">{{ loja_cidade }}</div>
      <div class="val">CNPJ: {{ cnpj }}</div>
      {% if telefone %}<div class="val">Tel: {{ telefone }}</div>{% endif %}
    </div>
    <div class="cell c" style="display:flex;flex-direction:column;gap:3px">
      <div style="font-weight:bold;font-size:15px;letter-spacing:1px">DFAT-e</div>
      <div class="val">Documento de Fatura Eletrônica</div>
      <div class="row" style="border:1px solid #000;margin-top:3px;align-items:stretch">
        <div style="flex:1;text-align:left;padding:2px 6px"><div>0 - Entrada</div><div>1 - Saída</div></div>
        <div style="border-left:1px solid #000;width:34px;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:18px">1</div>
      </div>
      <div class="val" style="margin-top:2px"><b>Nº:</b> {{ order.number }}</div>
      <div class="val"><b>Série:</b> 0</div>
      <div class="val"><b>Folha:</b> 1/1</div>
      <div class="lbl" style="margin-top:2px">Emissão: {{ emit }}</div>
    </div>
    <div class="cell c" style="flex:0 0 140px;display:flex;flex-direction:column;align-items:center;gap:3px">
      {% if qr_data_uri %}<img src="{{ qr_data_uri }}" alt="{{ order.number }}" style="width:108px;height:108px">{% endif %}
      <div class="val" style="font-family:monospace">{{ order.number }}</div>
    </div>
  </div>

  <div class="sec">
    <div class="sec-h">Destinatário</div>
    <div class="row">
      <div class="cell" style="flex:2"><div class="lbl">Nome / Razão social</div><div class="val">{{ a.recipient_name or order.email }}</div></div>
      <div class="cell"><div class="lbl">CNPJ / CPF</div><div class="val">{{ cpf }}</div></div>
      <div class="cell"><div class="lbl">Data de emissão</div><div class="val">{{ emit }}</div></div>
    </div>
    <div class="row" style="border-top:1px solid #000">
      <div class="cell" style="flex:2"><div class="lbl">Endereço</div><div class="val">{{ addr_dest }}</div></div>
      <div class="cell"><div class="lbl">Bairro</div><div class="val">{{ a.district or '—' }}</div></div>
      <div class="cell"><div class="lbl">CEP</div><div class="val">{{ a.zip or '—' }}</div></div>
    </div>
    <div class="row" style="border-top:1px solid #000">
      <div class="cell"><div class="lbl">Município</div><div class="val">{{ a.city or '—' }}</div></div>
      <div class="cell" style="flex:0 0 60px"><div class="lbl">UF</div><div class="val">{{ (a.state or '—')|upper }}</div></div>
      <div class="cell"><div class="lbl">Telefone</div><div class="val">{{ a.phone or '—' }}</div></div>
      <div class="cell" style="flex:2"><div class="lbl">E-mail</div><div class="val">{{ order.email }}</div></div>
    </div>
  </div>

  <div class="sec">
    <div class="sec-h">Transporte / entrega</div>
    <div class="row">
      <div class="cell"><div class="lbl">Transportadora / serviço</div><div class="val">{{ transportadora }}</div></div>
      <div class="cell" style="flex:2"><div class="lbl">Código de rastreio</div><div class="val" style="font-family:monospace">{{ tracking or '—' }}</div></div>
    </div>
    <div class="row" style="border-top:1px solid #000">
      <div class="cell"><div class="lbl">Status do envio</div><div class="val">{{ envio_label }}</div></div>
      <div class="cell" style="flex:2"><div class="lbl">Data/hora do status</div><div class="val">{{ envio_at or '—' }}</div></div>
    </div>
  </div>

  <div class="sec">
    <div class="sec-h">Cálculo dos valores</div>
    <div class="row">
      <div class="cell"><div class="lbl">Valor dos produtos</div><div class="val r">{{ m(order.items_total_cents) }}</div></div>
      <div class="cell"><div class="lbl">Desconto{% if cupom_pct %} (cupom {{ order.coupon_code }} · −{{ cupom_pct }}%){% endif %}</div>
        <div class="val r">{% if order.discount_cents %}− {{ m(order.discount_cents) }}{% else %}{{ m(0) }}{% endif %}</div></div>
      <div class="cell"><div class="lbl">Valor do frete{% if order.shipping_method %} ({{ order.shipping_method }}){% endif %}</div><div class="val r">{{ m(order.shipping_cents) }}</div></div>
      {% if juros %}<div class="cell"><div class="lbl">Juros do parcelamento</div><div class="val r">{{ m(juros) }}</div></div>{% endif %}
      <div class="cell"><div class="lbl">Valor total da fatura</div><div class="val r" style="font-weight:bold">{{ m(total_fatura) }}</div></div>
    </div>
  </div>

  <div class="sec">
    <div class="sec-h">Dados dos produtos / serviços</div>
    <table>
      <thead><tr>
        <th style="width:16%">Código</th><th>Descrição do produto / serviço</th>
        <th style="width:16%">Variação</th><th style="width:7%" class="c">Qtd</th>
        <th style="width:13%" class="r">Valor unit.</th><th style="width:13%" class="r">Valor total</th>
      </tr></thead>
      <tbody>
        {% for it in items %}<tr>
          <td>{{ it.sku }}</td><td>{{ it.name }}</td><td>{{ it.variant_label or '—' }}</td>
          <td class="c">{{ it.quantity }}</td><td class="r">{{ m(it.unit_price_cents) }}</td>
          <td class="r">{{ m((it.unit_price_cents or 0) * it.quantity) }}</td>
        </tr>{% endfor %}
      </tbody>
    </table>
  </div>

  <div class="sec">
    <div class="sec-h">Pagamento</div>
    <div class="row">
      <div class="cell" style="flex:2"><div class="lbl">Forma de pagamento</div><div class="val">{{ pagamento_desc }}</div></div>
      <div class="cell"><div class="lbl">Juros</div><div class="val r">{% if juros %}{{ m(juros) }}{% else %}Sem juros{% endif %}</div></div>
      <div class="cell"><div class="lbl">Situação</div><div class="val">{{ pay_status }}</div></div>
    </div>
    {% if order.coupon_code %}<div class="row" style="border-top:1px solid #000">
      <div class="cell"><div class="lbl">Cupom usado</div><div class="val" style="font-family:monospace">{{ order.coupon_code }}</div></div>
      <div class="cell"><div class="lbl">Redução</div><div class="val r">{% if cupom_pct %}−{{ cupom_pct }}%{% else %}—{% endif %} ({{ m(order.discount_cents) }})</div></div>
      <div class="cell" style="flex:2"></div>
    </div>{% endif %}
  </div>

  <div class="sec">
    <div class="sec-h">Dados adicionais</div>
    <div class="row"><div class="cell"><div class="lbl">Informações complementares</div><div class="val">{{ order.customer_note or '—' }}</div></div></div>
  </div>

  <p class="mt" style="font-size:9px">Documento não fiscal, gerado para conferência do pedido. Impresso em {{ agora }}.</p>
</div></body></html>"""
)


async def build_invoice_pdf(db: AsyncSession, order: Order) -> bytes:
    from weasyprint import HTML

    from app.modules.admin.models import StoreSettings
    from app.modules.orders.models import OrderEvent
    from app.modules.payment.models import Payment

    store = await db.get(StoreSettings, 1)
    pay = await db.scalar(
        select(Payment).where(Payment.order_id == order.id).order_by(Payment.created_at.desc())
    )
    events = list(
        await db.scalars(
            select(OrderEvent).where(OrderEvent.order_id == order.id).order_by(OrderEvent.created_at.desc())
        )
    )
    items = list(order.items)
    a = order.shipping_address_json or {}
    svc = order.shipping_service_json or {}
    saddr = (store.address_json if store else None) or {}

    parcelas = pay.installments if pay and pay.installments and pay.installments > 1 else 1
    juros = max(0, pay.amount_cents - order.grand_total_cents) if pay else 0
    if not pay:
        pagamento_desc = "—"
    elif pay.method == "credit_card":
        pagamento_desc = (
            f"Cartão de crédito — {parcelas}x de {_money(round(pay.amount_cents / parcelas))}"
            if parcelas > 1
            else "Cartão de crédito — à vista"
        )
    elif pay.method == "boleto":
        pagamento_desc = "Boleto bancário — à vista"
    elif pay.method == "pix":
        pagamento_desc = "PIX — à vista"
    else:
        pagamento_desc = pay.method

    cupom_pct = (
        round(order.discount_cents / order.items_total_cents * 100)
        if order.coupon_code and order.items_total_cents > 0
        else 0
    )
    envio_ev = next((e for e in events if e.to_status == order.status), None)

    from app.modules.orders.codes import order_qr_data_uri

    qr = order_qr_data_uri(order.number)

    loja_nome = (store.legal_name or store.store_name) if store else "Loja"
    html = _TEMPLATE.render(
        order=order,
        items=items,
        a=a,
        m=_money,
        loja_nome=loja_nome,
        addr_loja=_addr_line(saddr),
        loja_cidade=(
            " - ".join(x for x in (saddr.get("city"), saddr.get("state")) if x)
            + (f" — CEP {saddr['zip']}" if saddr.get("zip") else "")
        )
        or "—",
        cnpj=_mask_doc(store.cnpj if store else None),
        telefone=(store.contact_phone if store else None),
        emit=_fmt_dt(order.placed_at),
        agora=_fmt_dt(datetime.now(UTC)),
        cpf=_mask_doc(order.cpf),
        addr_dest=_addr_line(a),
        transportadora=(svc.get("carrier") or "Correios")
        + (f" · {order.shipping_method}" if order.shipping_method else ""),
        tracking=svc.get("tracking_code"),
        envio_label=_ENVIO_LABEL.get(order.status, "Pendente"),
        envio_at=_fmt_dt(envio_ev.created_at) if envio_ev else None,
        juros=juros,
        total_fatura=(pay.amount_cents if juros and pay else order.grand_total_cents),
        cupom_pct=cupom_pct,
        pagamento_desc=pagamento_desc,
        pay_status=(_PAYMENT_STATUS_PT.get(pay.status, pay.status) if pay else "—"),
        qr_data_uri=qr,
    )
    return HTML(string=html).write_pdf()
