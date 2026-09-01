"""Pipeline de imagem: converte todo upload para WebP e gera 3 tamanhos.

Retorna as keys (thumb/medium/zoom) + metadados da imagem original.
"""
from __future__ import annotations

import io
import uuid
from dataclasses import dataclass

from PIL import Image, ImageOps

from app.core.errors import ValidationError
from app.core.config import settings
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


def _resize_webp(img: Image.Image, max_side: int, quality: int) -> bytes:
    im = img.copy()
    im.thumbnail((max_side, max_side), Image.LANCZOS)
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")
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


def process_favicon(raw: bytes, *, prefix: str = "theme") -> str:
    """Redimensiona para 50x50 (quadrado, sem distorcer) e salva como .ico
    (com 32 e 16 embutidos p/ compatibilidade). Retorna a storage key."""
    img = _open_validated(raw)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    square = ImageOps.fit(img, (50, 50), Image.LANCZOS)
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
