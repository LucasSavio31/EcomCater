"""Relatório de faturamento em PDF (menu Faturamento) -- mesmo mecanismo de
`orders/invoice.py` (HTML+CSS -> PDF via WeasyPrint, sem navegador).
"""
from __future__ import annotations

from datetime import UTC, datetime

from jinja2 import Environment, select_autoescape
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.financial import service
from app.shared.timez import store_tz

_env = Environment(autoescape=select_autoescape(["html", "xml"]))

_METHOD_LABEL = {"credit_card": "Cartão de crédito", "pix": "Pix", "boleto": "Boleto"}
_METHOD_COLOR = {"credit_card": "#2563eb", "pix": "#16a34a", "boleto": "#d97706"}


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
    city = " - ".join(x for x in (a.get("city"), a.get("state")) if x)
    return " · ".join(x for x in (base, city) if x) or "—"


def _fmt_dt(dt: datetime | None) -> str:
    if not dt:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(store_tz()).strftime("%d/%m/%Y, %H:%M")


def _fmt_day(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(store_tz()).strftime("%d/%m/%Y")


_TEMPLATE = _env.from_string(
    """<!doctype html><html><head><meta charset="utf-8"><style>
@page { size: A4; margin: 12mm; }
#rel { font-family: "Liberation Sans", Arial, Helvetica, sans-serif; color:#000; font-size:11px; line-height:1.35; }
.box { border:1px solid #000; }
.row { display:flex; }
.cell { border-right:1px solid #000; padding:4px 8px; flex:1; }
.cell:last-child { border-right:0; }
.lbl { font-size:8px; text-transform:uppercase; letter-spacing:.3px; color:#333; }
.val { font-size:12px; }
.sec { border:1px solid #000; border-top:0; margin-top:0; }
.sec-h { background:#eee; font-weight:bold; font-size:9px; text-transform:uppercase; padding:3px 8px; border-bottom:1px solid #000; }
table { width:100%; border-collapse:collapse; }
th, td { border:1px solid #000; padding:4px 6px; text-align:left; vertical-align:middle; }
th { background:#eee; font-size:8px; text-transform:uppercase; }
.r { text-align:right; } .c { text-align:center; } .mt { margin-top:8px; }
.bar-track { background:#eee; border-radius:2px; height:10px; width:100%; overflow:hidden; }
.bar-fill { height:10px; }
.swatch { display:inline-block; width:9px; height:9px; border-radius:2px; margin-right:4px; vertical-align:middle; }
</style></head><body><div id="rel">

  <div class="row box">
    <div class="cell" style="flex:2">
      <div style="font-weight:bold;font-size:14px">{{ loja_nome }}</div>
      <div class="val">{{ addr_loja }}</div>
      <div class="val">CNPJ: {{ cnpj }}</div>
      {% if telefone %}<div class="val">Tel: {{ telefone }}</div>{% endif %}
    </div>
    <div class="cell c" style="flex:0 0 220px;display:flex;flex-direction:column;justify-content:center;gap:2px">
      <div style="font-weight:bold;font-size:15px;letter-spacing:.5px">RELATÓRIO DE FATURAMENTO</div>
      <div class="val">Período: {{ periodo_de }} até {{ periodo_ate }}</div>
      <div class="lbl">Gerado em {{ agora }}</div>
    </div>
  </div>

  <div class="sec">
    <div class="sec-h">Resumo do período</div>
    <div class="row">
      <div class="cell"><div class="lbl">Faturamento bruto</div><div class="val">{{ m(s.gross_cents) }}</div></div>
      <div class="cell"><div class="lbl">Custo dos produtos</div><div class="val">{{ m(s.cost_cents) }}</div></div>
      <div class="cell"><div class="lbl">Custo de frete</div><div class="val">{{ m(s.shipping_cents) }}</div></div>
      <div class="cell"><div class="lbl">Faturamento líquido</div><div class="val">{{ m(s.net_cents) }}</div></div>
    </div>
    <div class="row" style="border-top:1px solid #000">
      <div class="cell"><div class="lbl">Margem de lucratividade</div><div class="val">{{ s.margin_pct }}%</div></div>
      <div class="cell"><div class="lbl">Estornos</div><div class="val">{{ m(s.refunded_cents) }} · {{ s.refunds_count }}</div></div>
      <div class="cell"><div class="lbl">Cancelamentos</div><div class="val">{{ m(s.canceled_cents) }} · {{ s.canceled_count }}</div></div>
      <div class="cell"><div class="lbl">Total de pedidos</div><div class="val">{{ s.orders_total }}</div></div>
    </div>
  </div>

  <div class="sec mt" style="border-top:1px solid #000">
    <div class="sec-h">Faturamento por forma de pagamento</div>
    <table>
      <thead><tr>
        <th style="width:26%">Forma</th>
        <th class="r" style="width:16%">Faturamento</th>
        <th class="r" style="width:12%">Participação</th>
        <th class="r" style="width:12%">Conversão</th>
        <th style="width:34%">Participação no faturamento</th>
      </tr></thead>
      <tbody>
        {% for pm in payment_methods %}<tr>
          <td><span class="swatch" style="background:{{ pm.color }}"></span>{{ pm.label }}</td>
          <td class="r">{{ m(pm.gross_cents) }}</td>
          <td class="r">{{ pm.share_pct }}%</td>
          <td class="r">{{ pm.conversion_pct }}% ({{ pm.paid_count }}/{{ pm.placed_count }})</td>
          <td><div class="bar-track"><div class="bar-fill" style="width:{{ pm.share_pct }}%;background:{{ pm.color }}"></div></div></td>
        </tr>{% endfor %}
      </tbody>
    </table>
    <div style="padding:4px 8px;font-size:8px;color:#333">Conversão = dos pedidos gerados no período com essa forma de pagamento, quantos terminaram pagos.</div>
  </div>

  <div class="sec mt" style="border-top:1px solid #000">
    <div class="sec-h">Evolução no período</div>
    <table>
      <thead><tr>
        <th>Período</th><th class="r">Bruto</th><th class="r">Líquido</th>
        <th class="r">Estornos</th><th class="r">Cancelamentos</th><th class="c">Pedidos</th>
      </tr></thead>
      <tbody>
        {% for pt in series %}<tr>
          <td>{{ pt.label }}</td>
          <td class="r">{{ m(pt.gross_cents) }}</td>
          <td class="r">{{ m(pt.net_cents) }}</td>
          <td class="r">{{ m(pt.refunded_cents) }}</td>
          <td class="r">{{ m(pt.canceled_cents) }}</td>
          <td class="c">{{ pt.orders }}</td>
        </tr>{% endfor %}
      </tbody>
    </table>
  </div>

  <p class="mt" style="font-size:9px">Livro-caixa da loja — valores cumulativos e persistentes (não mudam se um pedido for excluído).</p>
</div></body></html>"""
)


async def build_financial_report_pdf(db: AsyncSession, win_start: datetime, win_end: datetime) -> bytes:
    from weasyprint import HTML

    from app.modules.admin.models import StoreSettings

    store = await db.get(StoreSettings, 1)
    s = await service.summary(db, win_start, win_end)

    payment_methods = [
        {
            **pm,
            "label": _METHOD_LABEL.get(pm["method"], pm["method"]),
            "color": _METHOD_COLOR.get(pm["method"], "#6b7280"),
        }
        for pm in s["payment_methods"]
    ]

    loja_nome = (store.legal_name or store.store_name) if store else "Loja"
    html = _TEMPLATE.render(
        s=s,
        series=s["series"],
        payment_methods=payment_methods,
        m=_money,
        loja_nome=loja_nome,
        addr_loja=_addr_line(store.address_json if store else None),
        cnpj=_mask_doc(store.cnpj if store else None),
        telefone=(store.contact_phone if store else None),
        periodo_de=_fmt_day(win_start),
        periodo_ate=_fmt_day(win_end),
        agora=_fmt_dt(datetime.now(UTC)),
    )
    return HTML(string=html).write_pdf()
