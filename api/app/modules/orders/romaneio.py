"""Romaneio de separação em PDF -- lista de itens pra separar no estoque dos
pedidos selecionados (Nº pedido, data, cliente, modelo, cor, número). Mesmo
mecanismo de `orders/invoice.py`/`financial/report.py` (HTML+CSS -> PDF via
WeasyPrint, sem navegador).
"""
from __future__ import annotations

import re
from datetime import UTC, datetime

from jinja2 import Environment, select_autoescape

from app.shared.timez import store_tz

_env = Environment(autoescape=select_autoescape(["html", "xml"]))

_COR_FROM_NAME_RE = re.compile(
    r"(?:BOTA\s+COTURNO|COTURNO|T[ÊE]NIS|TENIS|BOTA|SAPAT[ÊE]NIS|SAND[ÁA]LIA)\s+\S+\s+(.+)",
    re.I,
)


def _cor_from_name(name: str) -> str:
    m = _COR_FROM_NAME_RE.match((name or "").strip())
    return m.group(1).strip() if m else ""


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


def _cor_numero(item: dict) -> tuple[str, str]:
    attrs = item.get("variant_attrs") or {}
    cor = str(attrs.get("cor") or "").strip()
    numero = str(attrs.get("numero") or "").strip()
    label = str(item.get("variant_label") or "").strip()
    if not numero:
        m = re.search(r"\d{2,3}", label)
        numero = m.group(0) if m else label
    if not cor:
        cor = str(item.get("product_color") or "").strip() or _cor_from_name(item.get("name", ""))
        if not cor and "/" in label:
            cor = label.split("/", 1)[1].strip()
    return cor, numero


def _fmt_dt(raw: str | None) -> str:
    if not raw:
        return "—"
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return raw[:10]
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(store_tz()).strftime("%d/%m/%Y %H:%M")


def _now() -> str:
    return datetime.now(UTC).astimezone(store_tz()).strftime("%d/%m/%Y, %H:%M")


_TEMPLATE = _env.from_string(
    """<!doctype html><html><head><meta charset="utf-8"><style>
@page { size: A4; margin: 12mm; }
#rom { font-family: "Liberation Sans", Arial, Helvetica, sans-serif; color:#000; font-size:11px; line-height:1.35; }
.box { border:1px solid #000; }
.row { display:flex; }
.cell { border-right:1px solid #000; padding:4px 8px; flex:1; }
.cell:last-child { border-right:0; }
.lbl { font-size:8px; text-transform:uppercase; letter-spacing:.3px; color:#333; }
.val { font-size:12px; }
table { width:100%; border-collapse:collapse; margin-top:10px; }
th, td { border:1px solid #000; padding:4px 6px; text-align:left; vertical-align:top; }
th { background:#eee; font-size:8px; text-transform:uppercase; }
.c { text-align:center; }
.shade { background:#f7f7f7; }
</style></head><body><div id="rom">

  <div class="row box">
    <div class="cell" style="flex:2">
      <div style="font-weight:bold;font-size:14px">{{ loja_nome }}</div>
      <div class="val">{{ addr_loja }}</div>
      <div class="val">CNPJ: {{ cnpj }}</div>
      {% if telefone %}<div class="val">Tel: {{ telefone }}</div>{% endif %}
    </div>
    <div class="cell c" style="flex:0 0 220px;display:flex;flex-direction:column;justify-content:center;gap:2px">
      <div style="font-weight:bold;font-size:15px;letter-spacing:.5px">ROMANEIO DE SEPARAÇÃO</div>
      <div class="val">{{ pedidos_count }} pedido{{ '' if pedidos_count == 1 else 's' }} · {{ itens_count }} item{{ '' if itens_count == 1 else 's' }}</div>
      <div class="lbl">Gerado em {{ agora }}</div>
    </div>
  </div>

  <table>
    <thead><tr>
      <th style="width:12%">Nº Pedido</th>
      <th style="width:14%">Data</th>
      <th style="width:18%">Cliente</th>
      <th>Modelo</th>
      <th style="width:14%">Cor</th>
      <th class="c" style="width:9%">Número</th>
      <th class="c" style="width:7%">Qtd.</th>
    </tr></thead>
    <tbody>
      {% for row in rows %}<tr class="{{ 'shade' if row.shade else '' }}">
        <td>{{ row.number }}</td>
        <td>{{ row.placed_at }}</td>
        <td>{{ row.customer_name }}</td>
        <td>{{ row.name }}</td>
        <td>{{ row.cor or '—' }}</td>
        <td class="c">{{ row.numero or '—' }}</td>
        <td class="c">{{ row.quantity }}</td>
      </tr>{% endfor %}
    </tbody>
  </table>

  <p style="margin-top:8px;font-size:9px">Documento interno pra separação dos pedidos no estoque -- não é fiscal.</p>
</div></body></html>"""
)


def build_romaneio_pdf(orders: list[dict], *, store) -> bytes:
    from weasyprint import HTML

    rows = []
    shade = False
    for o in orders:
        shade = not shade
        for it in o.get("items") or []:
            cor, numero = _cor_numero(it)
            rows.append(
                {
                    "number": o["number"],
                    "placed_at": _fmt_dt(o.get("placed_at")),
                    "customer_name": o.get("customer_name") or "—",
                    "name": it.get("name", ""),
                    "cor": cor,
                    "numero": numero,
                    "quantity": it.get("quantity") or 0,
                    "shade": shade,
                }
            )

    loja_nome = (store.legal_name or store.store_name) if store else "Loja"
    html = _TEMPLATE.render(
        loja_nome=loja_nome,
        addr_loja=_addr_line(store.address_json if store else None),
        cnpj=_mask_doc(store.cnpj if store else None),
        telefone=(store.contact_phone if store else None),
        pedidos_count=len(orders),
        itens_count=len(rows),
        agora=_now(),
        rows=rows,
    )
    return HTML(string=html).write_pdf()
