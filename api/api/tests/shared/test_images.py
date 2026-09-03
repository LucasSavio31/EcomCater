"""Upload de imagem: WebP sem metadados; SVG sem script/metadata; GIF limpo."""
from __future__ import annotations

import io

from PIL import Image

from app.shared.images import _resize_webp, reencode_gif, sanitize_svg


def _jpeg_with_exif() -> Image.Image:
    im = Image.new("RGB", (64, 48), (200, 120, 40))
    exif = Image.Exif()
    exif[0x010F] = "ACME Cam"          # Make
    exif[0x0110] = "Model X"           # Model
    exif[0x0131] = "EvilEditor 9"      # Software
    buf = io.BytesIO()
    im.save(buf, format="JPEG", exif=exif)
    buf.seek(0)
    return Image.open(buf)


def test_resize_webp_has_no_metadata():
    src = _jpeg_with_exif()
    assert src.getexif()  # o original TEM exif

    out = _resize_webp(src, 32, 80)
    res = Image.open(io.BytesIO(out))
    assert res.format == "WEBP"
    assert not dict(res.getexif())          # sem EXIF
    for k in ("exif", "icc_profile", "xmp", "photoshop", "comment"):
        assert k not in res.info


def test_sanitize_svg_strips_script_and_metadata():
    raw = (
        b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" '
        b'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">'
        b'<!-- feito no Inkscape por Fulano -->'
        b'<metadata><rdf>autor: Fulano</rdf></metadata>'
        b'<title>logo-cliente</title><desc>marca da loja</desc>'
        b'<script>fetch("/x")</script>'
        b'<rect width="10" height="10" onload="alert(1)" inkscape:label="camada 1"/>'
        b'</svg>'
    )
    out = sanitize_svg(raw)
    low = out.lower()
    assert b"<script" not in low
    assert b"<metadata" not in low
    assert b"<title" not in low and b"<desc" not in low
    assert b"onload" not in low
    assert b"inkscape:" not in low
    assert b"<!--" not in out
    assert b"<rect" in low  # o desenho fica


def test_reencode_gif_drops_comment():
    im = Image.new("P", (8, 8))
    buf = io.BytesIO()
    im.save(buf, format="GIF", comment=b"segredo interno")
    cleaned = reencode_gif(buf.getvalue())
    assert b"segredo interno" not in cleaned
    assert Image.open(io.BytesIO(cleaned)).format == "GIF"
