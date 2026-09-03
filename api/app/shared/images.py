"""Pipeline de imagem: converte todo upload para WebP e gera 3 tamanhos.

Retorna as keys (thumb/medium/zoom) + metadados da imagem original.
"""
from __future__ import annotations

import io
import re
import uuid
from dataclasses import dataclass

from PIL import Image, ImageOps

from app.core.config import settings
from app.core.errors import ValidationError
from app.shared.storage import storage

# limites de segurança do upload
MAX_UPLOAD_BYTES = 15 * 1024 * 1024          # 15 MB por arquivo
MAX_PIXELS = 40_000_000                       # ~ 6300x6300 — barra "decompression bomb"
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


def _open_validated(raw: bytes) -> Image.Image:
    """Abre o upload com as travas de tamanho/formato e orientação EXIF."""
    if not raw:
        raise ValidationError("Arquivo de imagem vazio.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValidationError(
            f"Imagem muito grande (máx. {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)."
        )
    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()  # detecta arquivo corrompido / não-imagem
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
    except ValidationError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ValidationError("Arquivo enviado não é uma imagem válida.") from exc
    if img.width * img.height > MAX_PIXELS:
        raise ValidationError("Resolução da imagem acima do limite permitido.")
    return img


@dataclass
class ProcessedImage:
    thumb_key: str
    medium_key: str
    zoom_key: str
    original_filename: str
    original_width: int
    original_height: int


# chaves de metadado que o Pillow copia sozinho do arquivo original ao salvar
_META_KEYS = ("exif", "icc_profile", "xmp", "dpi", "photoshop", "comment", "iptc", "adobe")


def _strip_meta(im: Image.Image) -> None:
    """Remove EXIF (câmera/GPS/data), XMP, IPTC, ICC etc. do que vai ser servido.
    O Pillow copia essas chaves do original ao salvar se elas ficarem em `im.info`."""
    for k in _META_KEYS:
        im.info.pop(k, None)


def _resize_webp(img: Image.Image, max_side: int, quality: int) -> bytes:
    im = img.copy()
    im.thumbnail((max_side, max_side), Image.LANCZOS)
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")
    _strip_meta(im)
    buf = io.BytesIO()
    im.save(buf, format="WEBP", quality=quality, method=6)
    return buf.getvalue()


def whiten_bytes(raw: bytes) -> bytes:
    """Devolve uma versão BRANCA da imagem: mantém as formas (silhueta) e pinta
    tudo de branco. Funciona com fundo transparente ou fundo claro/branco —
    útil para tiras de logos de pagamento sobre rodapé escuro."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
    if img.mode == "RGBA":
        a = img.getchannel("A")
    else:
        # pixels escuros viram opacos; fundo claro vira transparente
        a = img.convert("L").point(lambda p: 255 - p)
    white = Image.new("RGBA", img.size, (255, 255, 255, 0))
    white.putalpha(a)
    buf = io.BytesIO()
    white.save(buf, format="PNG")
    return buf.getvalue()


# --------------------------------------------------------------------- SVG / GIF
_SVG_COMMENT = re.compile(rb"<!--.*?-->", re.DOTALL)
_SVG_META = re.compile(rb"<(metadata|desc|title)\b.*?</\1>", re.DOTALL | re.IGNORECASE)
_SVG_SCRIPT = re.compile(rb"<script\b.*?</script>", re.DOTALL | re.IGNORECASE)
_SVG_PI = re.compile(rb"<\?xml-stylesheet\b.*?\?>", re.DOTALL | re.IGNORECASE)
_SVG_ON_ATTR = re.compile(rb'\son[a-z]+\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)', re.IGNORECASE)
_SVG_EDITOR_ATTR = re.compile(rb'\s(?:sodipodi|inkscape|dc|cc|rdf|xmlns:(?:sodipodi|inkscape|dc|cc|rdf)):[a-z-]+\s*=\s*("[^"]*"|\'[^\']*\')', re.IGNORECASE)


def sanitize_svg(raw: bytes) -> bytes:
    """Tira do SVG: comentários, <metadata>/<title>/<desc>, <script>, handlers
    on*, atributos de editor (Inkscape/Sodipodi) e PIs de estilo. O que sobra é
    só o desenho — nada que identifique origem, autor ou rode código."""
    s = _SVG_COMMENT.sub(b"", raw)
    s = _SVG_META.sub(b"", s)
    s = _SVG_SCRIPT.sub(b"", s)
    s = _SVG_PI.sub(b"", s)
    s = _SVG_ON_ATTR.sub(b"", s)
    s = _SVG_EDITOR_ATTR.sub(b"", s)
    return s.strip()


def reencode_gif(raw: bytes) -> bytes:
    """Reescreve o GIF (mantendo animação) sem blocos de comentário/XMP/metadados."""
    try:
        im = Image.open(io.BytesIO(raw))
        buf = io.BytesIO()
        im.info.pop("comment", None)
        im.info.pop("xmp", None)
        im.save(buf, format="GIF", save_all=getattr(im, "is_animated", False), optimize=False)
        return buf.getvalue()
    except Exception:  # noqa: BLE001
        return raw  # se algo der errado, melhor o gif original que nada


def process_favicon(raw: bytes, *, prefix: str = "theme") -> str:
    """Redimensiona para 50x50 (quadrado, sem distorcer) e salva como .ico
    (com 32 e 16 embutidos p/ compatibilidade). Retorna a storage key."""
    img = _open_validated(raw)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    square = ImageOps.fit(img, (50, 50), Image.LANCZOS)
    _strip_meta(square)
    buf = io.BytesIO()
    square.save(buf, format="ICO", sizes=[(50, 50), (32, 32), (16, 16)])
    key = f"{prefix}/{uuid.uuid4().hex}/favicon.ico"
    storage.save(key, buf.getvalue(), "image/x-icon")
    return key


def process_image(
    raw: bytes,
    original_filename: str,
    *,
    prefix: str = "products",
) -> ProcessedImage:
    img = _open_validated(raw)
    width, height = img.size
    q = settings.image_webp_quality
    folder = f"{prefix}/{uuid.uuid4().hex}"

    variants = {
        "thumb": settings.image_thumb_size,
        "medium": settings.image_medium_size,
        "zoom": settings.image_zoom_size,
    }
    keys: dict[str, str] = {}
    for name, size in variants.items():
        data = _resize_webp(img, size, q)
        key = f"{folder}/{name}.webp"
        storage.save(key, data, "image/webp")
        keys[name] = key

    return ProcessedImage(
        thumb_key=keys["thumb"],
        medium_key=keys["medium"],
        zoom_key=keys["zoom"],
        original_filename=original_filename,
        original_width=width,
        original_height=height,
    )
