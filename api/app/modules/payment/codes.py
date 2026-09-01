"""Imagens (data URI) para o checkout: QR do PIX e código de barras do boleto.

Geradas no servidor e embutidas direto na resposta — a página de "obrigado"
não precisa de outra requisição (nem de token) para mostrá-las.
"""
from __future__ import annotations

import base64
import io
import logging

logger = logging.getLogger("payment.codes")


def pix_qr_data_uri(emv: str) -> str | None:
    """QR Code (PNG data URI) do "copia e cola" do PIX."""
    if not emv:
        return None
    try:
        import segno

        return segno.make(emv, error="m").png_data_uri(scale=6, border=2, dark="#111111")
    except Exception:  # noqa: BLE001
        logger.exception("falha ao gerar QR do PIX")
        return None


def boleto_barcode_data_uri(linha_digitavel: str) -> str | None:
    """Código de barras (SVG data URI, ITF — padrão de boleto) a partir da
    linha digitável/código de barras do boleto."""
    digits = "".join(c for c in (linha_digitavel or "") if c.isdigit())
    if not digits:
        return None
    if len(digits) % 2:  # ITF exige quantidade par de dígitos
        digits = digits[:-1]
    try:
        import barcode
        from barcode.writer import SVGWriter

        code = barcode.get("itf", digits, writer=SVGWriter())
        buf = io.BytesIO()
        code.write(buf, options={"write_text": False, "quiet_zone": 2})
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/svg+xml;base64,{b64}"
    except Exception:  # noqa: BLE001
        logger.exception("falha ao gerar código de barras do boleto")
        return None
