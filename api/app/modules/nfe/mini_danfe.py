"""DANFE Simplificado – Etiqueta (NT 2020.004) — versão compacta pra
impressora térmica 10x15, no mesmo espírito do que Mercado Livre/Shopee
imprimem junto com a etiqueta de envio.

Diferença pro DANFE cheio (`brazilfiscalreport`, gerado em
`service._gerar_danfe`): sem lista de itens (a norma técnica explicitamente
não exige), sem QR Code (só o código de barras da chave é obrigatório aqui).
Campos exigidos pela NT 2020.004 v1.10:
- "DANFE Simplificado – Etiqueta"
- Chave de acesso + código de barras (canto superior direito)
- Protocolo de autorização
- Emitente: nome/razão social, UF, CNPJ, IE
- Dados gerais: tipo de operação, série, número, data de emissão
- Destinatário: nome/razão social, UF, CNPJ/CPF, IE (quando houver)
- Fonte >= 6pt, títulos em negrito e maiúsculo, largura mínima 55mm.
"""
from __future__ import annotations

import io

from lxml import etree

_NS = {"n": "http://www.portalfiscal.inf.br/nfe"}


def _text(root, xpath: str) -> str:
    el = root.find(xpath, _NS)
    return (el.text or "").strip() if el is not None else ""


def _mask_doc(doc: str) -> str:
    d = "".join(ch for ch in doc if ch.isdigit())
    if len(d) == 14:
        return f"{d[0:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"
    if len(d) == 11:
        return f"{d[0:3]}.{d[3:6]}.{d[6:9]}-{d[9:11]}"
    return doc


def _fmt_data(dh: str) -> str:
    # "2026-09-19T15:04:00-03:00" -> "19/09/2026 15:04"
    try:
        data, hora = dh.split("T")
        y, m, d = data.split("-")
        hh, mm = hora[:5].split(":")
        return f"{d}/{m}/{y} {hh}:{mm}"
    except Exception:
        return dh


def build_mini_danfe(xml_bytes: bytes, protocolo: str | None) -> bytes:
    """Monta o PDF 100x150mm a partir do XML já assinado (o mesmo salvo em
    `NfeDocument.xml_key`) + o protocolo de autorização (guardado à parte no
    banco, não faz parte do XML de envio que a gente guarda)."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    root = etree.fromstring(xml_bytes)
    inf_nfe = root.find(".//n:infNFe", _NS)
    chave = (inf_nfe.get("Id") or "")[3:]  # tira o prefixo "NFe"

    tp_amb = _text(root, ".//n:ide/n:tpAmb")
    tp_nf = _text(root, ".//n:ide/n:tpNF")
    serie = _text(root, ".//n:ide/n:serie")
    numero = _text(root, ".//n:ide/n:nNF")
    dh_emi = _text(root, ".//n:ide/n:dhEmi")

    emit_nome = _text(root, ".//n:emit/n:xNome")
    emit_cnpj = _text(root, ".//n:emit/n:CNPJ")
    emit_ie = _text(root, ".//n:emit/n:IE")
    emit_uf = _text(root, ".//n:emit/n:enderEmit/n:UF")

    dest_nome = _text(root, ".//n:dest/n:xNome")
    dest_cnpj = _text(root, ".//n:dest/n:CNPJ")
    dest_cpf = _text(root, ".//n:dest/n:CPF")
    dest_doc = dest_cnpj or dest_cpf
    dest_ie = _text(root, ".//n:dest/n:IE")
    dest_uf = _text(root, ".//n:dest/n:enderDest/n:UF")

    valor_total = _text(root, ".//n:total/n:ICMSTot/n:vNF")

    # ------------------------------------------------------------- barcode
    import barcode as barcode_lib
    from barcode.writer import ImageWriter

    barcode_buf = io.BytesIO()
    barcode_lib.get("code128", chave, writer=ImageWriter()).write(
        barcode_buf, options={"write_text": False, "module_height": 10.0, "quiet_zone": 1.0}
    )
    barcode_buf.seek(0)

    # --------------------------------------------------------------- pdf
    pdf = FPDF(orientation="P", unit="mm", format=(100, 150))
    pdf.set_margins(3, 3, 3)
    pdf.set_auto_page_break(False)
    pdf.add_page()

    def title(text: str, size: float = 8) -> None:
        pdf.set_font("Helvetica", "B", size)
        pdf.cell(0, 4.5, text.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def value(text: str, size: float = 8) -> None:
        pdf.set_font("Helvetica", "", size)
        pdf.multi_cell(0, 4, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, "DANFE SIMPLIFICADO - ETIQUETA", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if tp_amb == "2":
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(200, 0, 0)
        pdf.cell(0, 4, "HOMOLOGACAO - SEM VALOR FISCAL", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)
    pdf.ln(1)

    # chave de acesso + código de barras, canto superior (a norma pede
    # "canto superior direito" -- aqui em largura cheia por legibilidade
    # numa etiqueta estreita, o que a norma permite: "em qualquer sentido")
    title("Chave de acesso")
    value(" ".join(chave[i : i + 4] for i in range(0, len(chave), 4)), size=7)
    pdf.image(barcode_buf, x=3, y=pdf.get_y(), w=94, h=12)
    pdf.set_y(pdf.get_y() + 13)

    title("Protocolo de autorização")
    value(protocolo or "-")
    pdf.ln(1)

    title("Emitente")
    value(emit_nome)
    value(f"CNPJ: {_mask_doc(emit_cnpj)}   UF: {emit_uf}")
    value(f"IE: {emit_ie or '-'}")
    pdf.ln(1)

    title("Dados da NF-e")
    value(f"{'ENTRADA' if tp_nf == '0' else 'SAIDA'} | Série: {serie}  Nº: {numero}")
    value(f"Emissão: {_fmt_data(dh_emi)}")
    pdf.ln(1)

    title("Destinatário / Remetente")
    value(dest_nome)
    value(f"{'CNPJ' if dest_cnpj else 'CPF'}: {_mask_doc(dest_doc)}   UF: {dest_uf}")
    value(f"IE: {dest_ie or '-'}")
    pdf.ln(1)

    title("Valor total da NF-e")
    value(f"R$ {float(valor_total or 0):.2f}".replace(".", ","))

    return bytes(pdf.output())
