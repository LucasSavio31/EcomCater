"""Tarja de NF-e pra colar no pé da etiqueta de envio ("Gerar Etq/NFe" --
etiqueta + NF-e numa página só). Usa o mesmo gerador Code128 (python-barcode)
já usado no DANFE simplificado (`nfe/mini_danfe.py`), só que numa tarja
compacta em vez de uma etiqueta térmica inteira.
"""
from __future__ import annotations

import base64
import io

from jinja2 import Environment, select_autoescape

_env = Environment(autoescape=select_autoescape(["html", "xml"]))

_TEMPLATE = _env.from_string(
    """<!doctype html><html><head><meta charset="utf-8"><style>
@page { size: {{ width_mm }}mm {{ height_mm }}mm; margin: 0; }
body { margin:0; font-family: "Liberation Sans", Arial, Helvetica, sans-serif; }
* { box-sizing: border-box; }
#tarja { border:1.5px solid #000; width:100%; }
.h { text-align:center; font-weight:bold; font-size:11px; padding:3px 0; border-bottom:1px solid #000; text-transform:uppercase; letter-spacing:.3px; background:#000; color:#fff; }
.row { display:flex; border-bottom:1px solid #000; font-size:9px; }
.row .f { flex:1; padding:3px 6px; border-right:1px solid #000; white-space:nowrap; }
.row .f:last-child { border-right:0; }
.row .lbl { font-weight:bold; }
.bc { text-align:center; padding:4px 0 0; }
.bc img { height:34px; }
.chave-lbl { font-size:7px; text-transform:uppercase; letter-spacing:.3px; padding:2px 6px 0; }
.key { text-align:center; font-family:"Liberation Mono", monospace; font-size:10px; font-weight:bold; padding-bottom:3px; letter-spacing:.5px; }
</style></head><body>
<div id="tarja">
  <div class="h">Documento Fiscal</div>
  <div class="row">
    <div class="f"><span class="lbl">Tipo:</span> Remessa</div>
    <div class="f"><span class="lbl">NF:</span> {{ numero }}</div>
    <div class="f"><span class="lbl">Série:</span> {{ serie }}</div>
    <div class="f"><span class="lbl">Emissão:</span> {{ emissao }}</div>
  </div>
  <div class="bc"><img src="{{ barcode_data_uri }}"></div>
  <div class="chave-lbl">Chave de acesso</div>
  <div class="key">{{ chave_grouped }}</div>
</div>
</body></html>"""
)


def _barcode_data_uri(chave: str) -> str:
    import barcode as barcode_lib
    from barcode.writer import ImageWriter

    buf = io.BytesIO()
    barcode_lib.get("code128", chave, writer=ImageWriter()).write(
        buf, options={"write_text": False, "module_height": 10.0, "quiet_zone": 1.0}
    )
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def _group_chave(chave: str) -> str:
    return " ".join(chave[i : i + 4] for i in range(0, len(chave), 4))


def build_nfe_strip_pdf(
    *,
    numero: int | None,
    serie: int | None,
    emissao: str,
    chave: str,
    width_mm: float = 100.0,
    height_mm: float = 28.0,
) -> bytes:
    from weasyprint import HTML

    html = _TEMPLATE.render(
        numero=numero if numero is not None else "—",
        serie=serie if serie is not None else "—",
        emissao=emissao,
        barcode_data_uri=_barcode_data_uri(chave),
        chave_grouped=_group_chave(chave),
        width_mm=width_mm,
        height_mm=height_mm,
    )
    return HTML(string=html).write_pdf()
