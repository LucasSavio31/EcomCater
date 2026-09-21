"""Orquestra a geração dos quadros de giro 360° com IA (RIFE) -- roda em
lote, 100% offline/CPU, disparada em background quando as fotos de um
produto mudam (adicionar/excluir/reordenar) e o giro 360° está ligado em
Aparência → Página de produto.

Cada par de fotos adjacentes (na ordem de exibição) só vira quadros
intermediários se `foreground_similarity` disser que são ângulos parecidos
o bastante -- senão fica como uma troca direta de foto (comportamento atual,
sem regressão). O resultado final (fotos originais + quadros gerados, na
ordem certa de reprodução) fica em `Product.spin_frames_json`; o front usa
essa lista quando não-vazia, senão cai pras fotos originais.
"""
from __future__ import annotations

import logging
import uuid
from asyncio import to_thread

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.modules.products.models import Product
from app.modules.products.spin_ai.interpolate import interpolate_between
from app.modules.products.spin_ai.similarity import SIMILARITY_THRESHOLD, foreground_similarity
from app.shared.storage import storage

logger = logging.getLogger("products.spin_ai")

MIN_IMAGES = 4
_FRAMES_PER_PAIR = 2


async def maybe_trigger(db: AsyncSession, product: Product, background) -> None:
    """Chama logo depois de add/excluir/reordenar imagens (produto já
    carregado com `.images`). Só agenda o job pesado se o giro 360° estiver
    ligado e o produto tiver fotos suficientes; senão limpa quadros antigos
    (produto caiu abaixo do mínimo, ou o recurso foi desligado depois)."""
    from app.modules.theme.service import get_theme

    theme = await get_theme(db)
    should_have_frames = theme.product_360_enabled and len(product.images) >= MIN_IMAGES
    if not should_have_frames:
        if product.spin_frames_json:
            product.spin_frames_json = []
        return
    if background is not None:
        background.add_task(generate_spin_frames, product.id)
    else:
        await generate_spin_frames(product.id)


def _build_sequence_sync(images: list[tuple[str, str]]) -> list[str]:
    """Roda numa thread (`asyncio.to_thread`) -- lê/grava storage e chama o
    modelo de IA, tudo síncrono e pesado o bastante pra travar o event loop
    se rodasse direto. `images`: [(id, zoom_key), ...] já na ordem certa."""
    sequence: list[str] = []
    for idx, (img_id, zoom_key) in enumerate(images):
        sequence.append(storage.url(zoom_key))
        if idx == len(images) - 1:
            continue
        _next_id, next_key = images[idx + 1]
        try:
            b0 = storage.read(zoom_key)
            b1 = storage.read(next_key)
            if foreground_similarity(b0, b1) < SIMILARITY_THRESHOLD:
                continue
            frames = interpolate_between(b0, b1, n_frames=_FRAMES_PER_PAIR)
            for i, frame_bytes in enumerate(frames):
                key = f"products/spin/{img_id}/{i}.webp"
                storage.save(key, frame_bytes, "image/webp")
                sequence.append(storage.url(key))
        except Exception:  # noqa: BLE001 -- 1 par ruim não pode travar o produto inteiro
            logger.exception("falha ao gerar quadros de IA entre imagens %s e %s", img_id, _next_id)
    return sequence


async def generate_spin_frames(product_id: uuid.UUID) -> None:
    async with SessionLocal() as db:
        try:
            from app.modules.theme.service import get_theme

            product = await db.scalar(
                select(Product).where(Product.id == product_id).options(selectinload(Product.images))
            )
            if not product:
                return
            theme = await get_theme(db)
            if not theme.product_360_enabled or len(product.images) < MIN_IMAGES:
                if product.spin_frames_json:
                    product.spin_frames_json = []
                    await db.commit()
                return

            # mesma ordem usada em `service._detail_out` (primária primeiro,
            # depois por posição) -- a mesma que a galeria da PDP mostra.
            images = sorted(product.images, key=lambda i: (not i.is_primary, i.position))
            pairs_info = [(str(i.id), i.zoom_key) for i in images]
            sequence = await to_thread(_build_sequence_sync, pairs_info)

            product.spin_frames_json = sequence
            await db.commit()
            logger.info(
                "giro 360° gerado pro produto %s: %d fotos -> %d quadros",
                product_id, len(images), len(sequence),
            )
        except Exception:  # noqa: BLE001 -- job de fundo, nunca pode propagar
            logger.exception("falha ao gerar giro 360° do produto %s", product_id)
            await db.rollback()
