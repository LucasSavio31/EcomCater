"""Relatório do painel (Dashboard) em PDF -- MESMO layout do relatório de
Faturamento (`financial/report.py`): HTML+CSS -> PDF via WeasyPrint, sem
navegador, cabeçalho com os dados da loja + período filtrado.
"""
from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from xml.sax.saxutils import escape as _xml_escape

from jinja2 import Environment, select_autoescape
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.schemas import DashboardOut
from app.shared.timez import parse_day_bound, store_tz

_env = Environment(autoescape=select_autoescape(["html", "xml"]))

# mesmas cores do gráfico `AbcCurve` do painel (admin/src/components/dashboard-charts.tsx)
_CLS_COLOR = {"A": "#16a34a", "B": "#d97706", "C": "#94a3b8"}


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


def _nice_max(v: float) -> float:
    if v <= 0:
        return 1
    mag = 10 ** math.floor(math.log10(v))
    n = v / mag
    step = 1 if n <= 1 else 2 if n <= 2 else 5 if n <= 5 else 10
    return step * mag


def _abc_chart_svg(points: list[dict]) -> str:
    """SVG estático da curva ABC -- MESMO desenho do gráfico `AbcCurve` do
    painel (barras de faturamento por produto, coloridas pela classe A/B/C,
    + linha do acumulado com a marca dos 80%), gerado em Python porque o
    WeasyPrint não roda JS."""
    if not points:
        return ""

    w, h = 700, 230
    pad_t, pad_r, pad_b, pad_l = 18, 50, 34, 70
    iw = w - pad_l - pad_r
    ih = h - pad_t - pad_b
    n = len(points)
    max_rev = _nice_max(max(1, max(p["revenue_cents"] for p in points)))
    bw = max(2.0, (iw / n) * 0.7)

    def cx(i: float) -> float:
        return pad_l + (i + 0.5) * (iw / n)

    def y_rev(c: float) -> float:
        return pad_t + ih - (c / max_rev) * ih

    def y_pct(p: float) -> float:
        return pad_t + ih - (p / 100) * ih

    parts = [f'<svg viewBox="0 0 {w} {h}" style="width:100%;height:auto;font-family:Arial,Helvetica,sans-serif">']

    for f in (0, 0.25, 0.5, 0.75, 1):
        yy = pad_t + ih - f * ih
        parts.append(
            f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{w - pad_r}" y2="{yy:.1f}" stroke="#e5e7eb" stroke-width="1"/>'
            f'<text x="{pad_l - 6}" y="{yy + 3:.1f}" text-anchor="end" font-size="9" fill="#6b7280">{_money(round(f * max_rev))}</text>'
            f'<text x="{w - pad_r + 6}" y="{yy + 3:.1f}" font-size="9" fill="#6b7280">{round(f * 100)}%</text>'
        )

    y80 = y_pct(80)
    parts.append(
        f'<line x1="{pad_l}" y1="{y80:.1f}" x2="{w - pad_r}" y2="{y80:.1f}" stroke="#16a34a" '
        f'stroke-width="1" stroke-dasharray="4 3"/>'
    )

    for i, p in enumerate(points):
        yy = y_rev(p["revenue_cents"])
        color = _CLS_COLOR.get(p["cls"], "#94a3b8")
        parts.append(
            f'<rect x="{cx(i) - bw / 2:.1f}" y="{yy:.1f}" width="{bw:.1f}" '
            f'height="{pad_t + ih - yy:.1f}" fill="{color}" rx="1"/>'
        )

    line_pts = " ".join(f"{cx(i):.1f},{y_pct(p['cum_pct']):.1f}" for i, p in enumerate(points))
    parts.append(f'<polyline points="{line_pts}" fill="none" stroke="#111827" stroke-width="2"/>')
    for i, p in enumerate(points):
        parts.append(f'<circle cx="{cx(i):.1f}" cy="{y_pct(p["cum_pct"]):.1f}" r="2.5" fill="#111827"/>')

    every_n = max(1, math.ceil(n / 10))
    for i, p in enumerate(points):
        if i % every_n == 0 or i == n - 1:
            name = p["name"][:10] + "…" if len(p["name"]) > 10 else p["name"]
            parts.append(
                f'<text x="{cx(i):.1f}" y="{h - 6}" text-anchor="middle" font-size="8" '
                f'fill="#6b7280">{_xml_escape(name)}</text>'
            )

    parts.append("</svg>")
    return "".join(parts)


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
      <div style="font-weight:bold;font-size:15px;letter-spacing:.5px">RELATÓRIO DO PAINEL</div>
      <div class="val">Período: {{ periodo_de }} até {{ periodo_ate }}</div>
      <div class="lbl">Gerado em {{ agora }}</div>
    </div>
  </div>

  <div class="sec">
    <div class="sec-h">Resumo do período</div>
    <div class="row">
      <div class="cell"><div class="lbl">Pedidos no período</div><div class="val">{{ d.orders_period }}</div></div>
      <div class="cell"><div class="lbl">Faturamento no período</div><div class="val">{{ m(d.revenue_period_cents) }}</div></div>
      <div class="cell"><div class="lbl">Aguardando pagamento</div><div class="val">{{ d.orders_pending }}</div></div>
      <div class="cell"><div class="lbl">Pendentes de envio</div><div class="val">{{ d.orders_to_ship }}</div></div>
    </div>
    <div class="row" style="border-top:1px solid #000">
      <div class="cell"><div class="lbl">Atrasados (+2 dias)</div><div class="val">{{ d.orders_late }}</div></div>
      <div class="cell"><div class="lbl">Cancelados no período</div><div class="val">{{ d.orders_canceled }}</div></div>
      <div class="cell"><div class="lbl">Estornados no período</div><div class="val">{{ d.orders_refunded }}</div></div>
      <div class="cell"><div class="lbl">Total de pedidos (histórico)</div><div class="val">{{ d.total_orders_all_time }}</div></div>
    </div>
  </div>

  <div class="sec mt" style="border-top:1px solid #000">
    <div class="sec-h">Curva ABC de produtos</div>
    {% if not d.abc_curve %}<div style="padding:6px 8px">Sem vendas no período.</div>{% else %}
    <div style="padding:8px">{{ abc_svg|safe }}</div>
    <div style="padding:0 8px 6px;display:flex;gap:16px;font-size:8px;color:#333">
      <span><span class="swatch" style="background:#16a34a"></span>Classe A (até 80%)</span>
      <span><span class="swatch" style="background:#d97706"></span>Classe B (80–95%)</span>
      <span><span class="swatch" style="background:#94a3b8"></span>Classe C (95–100%)</span>
    </div>
    <table>
      <thead><tr>
        <th>Produto</th><th class="r" style="width:16%">Faturamento</th>
        <th class="r" style="width:14%">Acumulado</th><th class="c" style="width:10%">Classe</th>
      </tr></thead>
      <tbody>
        {% for p in d.abc_curve %}<tr>
          <td>{{ p.name }}</td>
          <td class="r">{{ m(p.revenue_cents) }}</td>
          <td class="r">{{ p.cum_pct }}%</td>
          <td class="c"><span class="swatch" style="background:{{ cls_color(p.cls) }}"></span>{{ p.cls }}</td>
        </tr>{% endfor %}
      </tbody>
    </table>
    {% endif %}
  </div>

  <div class="sec mt" style="border-top:1px solid #000">
    <div class="sec-h">Top 10 produtos mais vendidos</div>
    {% if not d.top_products %}<div style="padding:6px 8px">Sem vendas no período.</div>{% else %}
    <table>
      <thead><tr>
        <th style="width:6%" class="c">#</th><th>Produto</th><th style="width:18%">SKU</th>
        <th class="c" style="width:10%">Qtd.</th><th class="r" style="width:16%">Faturamento</th>
      </tr></thead>
      <tbody>
        {% for p in d.top_products %}<tr>
          <td class="c">{{ loop.index }}</td>
          <td>{{ p.name }}</td>
          <td>{{ p.sku or '—' }}</td>
          <td class="c">{{ p.units }}</td>
          <td class="r">{{ m(p.revenue_cents) }}</td>
        </tr>{% endfor %}
      </tbody>
    </table>
    {% endif %}
  </div>

  <div class="sec mt" style="border-top:1px solid #000">
    <div class="sec-h">Top 10 estados que mais vendem</div>
    {% if not d.top_states %}<div style="padding:6px 8px">Sem vendas no período.</div>{% else %}
    <table>
      <thead><tr>
        <th style="width:6%" class="c">#</th><th style="width:10%">UF</th>
        <th class="c" style="width:12%">Pedidos</th><th class="r" style="width:16%">Faturamento</th>
        <th style="width:40%">Participação</th>
      </tr></thead>
      <tbody>
        {% for s in d.top_states %}<tr>
          <td class="c">{{ loop.index }}</td>
          <td>{{ s.state }}</td>
          <td class="c">{{ s.orders }}</td>
          <td class="r">{{ m(s.revenue_cents) }}</td>
          <td><div class="bar-track"><div class="bar-fill" style="width:{{ s.pct }}%;background:#2563eb"></div></div></td>
        </tr>{% endfor %}
      </tbody>
    </table>
    {% endif %}
  </div>

  <p class="mt" style="font-size:9px">Pedidos/faturamento/cancelamentos/estornos vêm do livro-caixa (cumulativos, sobrevivem à exclusão de pedidos). Curva ABC, top produtos e top estados vêm dos pedidos pagos no período.</p>
</div></body></html>"""
)


async def build_dashboard_report_pdf(
    db: AsyncSession, data: DashboardOut, date_from: str | None, date_to: str | None
) -> bytes:
    from weasyprint import HTML

    from app.modules.admin.models import StoreSettings

    store = await db.get(StoreSettings, 1)

    now = datetime.now(UTC)
    win_start = parse_day_bound(date_from, end=False)
    win_end = parse_day_bound(date_to, end=True)
    if win_start is None and win_end is None:
        win_end = now
        win_start = now - timedelta(days=30)
    elif win_start is None:
        win_start = win_end - timedelta(days=30)
    elif win_end is None:
        win_end = now

    # participação relativa (barra) do estado -- em cima do maior, não do
    # total, pra ficar legível igual a barra de forma de pagamento do
    # relatório de Faturamento.
    max_state_rev = max((s.revenue_cents for s in data.top_states), default=0) or 1
    states = [
        {**s.model_dump(), "pct": round(s.revenue_cents / max_state_rev * 100, 1)}
        for s in data.top_states
    ]

    loja_nome = (store.legal_name or store.store_name) if store else "Loja"
    html = _TEMPLATE.render(
        d={**data.model_dump(), "top_states": states},
        m=_money,
        abc_svg=_abc_chart_svg([p.model_dump() for p in data.abc_curve]),
        cls_color=lambda c: _CLS_COLOR.get(c, "#6b7280"),
        loja_nome=loja_nome,
        addr_loja=_addr_line(store.address_json if store else None),
        cnpj=_mask_doc(store.cnpj if store else None),
        telefone=(store.contact_phone if store else None),
        periodo_de=_fmt_day(win_start),
        periodo_ate=_fmt_day(win_end),
        agora=_fmt_dt(now),
    )
    return HTML(string=html).write_pdf()
