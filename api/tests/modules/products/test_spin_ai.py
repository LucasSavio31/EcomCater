"""Testes do módulo `products.spin_ai`: heurística de semelhança e a
orquestração da geração de quadros (a inferência de IA de verdade -- lenta,
~2-5s por quadro -- é mockada; a qualidade real já foi validada manualmente
com fotos reais da loja antes de integrar)."""
from __future__ import annotations

import io
import uuid

import pytest
from PIL import Image
from sqlalchemy import select

from app.modules.products.models import Product, ProductImage
from app.modules.products.spin_ai import service as spin_ai_service
from app.modules.products.spin_ai.similarity import foreground_similarity
from app.modules.theme.service import update_theme


def _solid_image(color: tuple[int, int, int], size: int = 64) -> bytes:
    """Fundo branco com um quadrado colorido no centro -- simula uma foto de
    produto em fundo branco sem precisar de arquivos reais."""
    im = Image.new("RGB", (size, size), "white")
    box = [(size * 0.3, size * 0.3), (size * 0.7, size * 0.7)]
    for x in range(int(box[0][0]), int(box[1][0])):
        for y in range(int(box[0][1]), int(box[1][1])):
            im.putpixel((x, y), color)
    buf = io.BytesIO()
    im.save(buf, format="WEBP")
    return buf.getvalue()


def test_foreground_similarity_same_silhouette_scores_high():
    a = _solid_image((100, 60, 20))
    b = _solid_image((90, 55, 25))  # mesma posição/tamanho, cor levemente diferente
    assert foreground_similarity(a, b) > 0.9


def test_foreground_similarity_different_composition_scores_low():
    im = Image.new("RGB", (64, 64), "white")
    for x in range(64):
        for y in range(64):
            im.putpixel((x, y), (120, 80, 30))  # ocupa a imagem inteira
    buf = io.BytesIO()
    im.save(buf, format="WEBP")
    full = buf.getvalue()

    small = _solid_image((120, 80, 30))
    assert foreground_similarity(full, small) < spin_ai_service.SIMILARITY_THRESHOLD


async def _make_product_with_images(db, n: int, *, wc_id: int) -> Product:
    from app.shared.storage import storage

    product = Product(
        wc_id=wc_id,
        name=f"Produto Spin {wc_id}",
        slug=f"produto-spin-{wc_id}",
        status="active",
        price_cents=10000,
    )
    db.add(product)
    await db.flush()

    for i in range(n):
        data = _solid_image((10 * i, 50, 80))
        key = f"products/spin-test/{product.id}/{i}.webp"
        storage.save(key, data, "image/webp")
        db.add(
            ProductImage(
                product_id=product.id,
                position=i,
                is_primary=(i == 0),
                thumb_key=key,
                medium_key=key,
                zoom_key=key,
            )
        )
    await db.flush()
    await db.refresh(product, ["images"])
    return product


@pytest.mark.asyncio
async def test_maybe_trigger_skips_when_360_disabled(db):
    await update_theme(db, {"product_360_enabled": False})
    product = await _make_product_with_images(db, 4, wc_id=90001)

    await spin_ai_service.maybe_trigger(db, product, background=None)
    await db.commit()

    row = await db.scalar(select(Product).where(Product.id == product.id))
    assert row.spin_frames_json == []


@pytest.mark.asyncio
async def test_maybe_trigger_skips_when_too_few_images(db):
    await update_theme(db, {"product_360_enabled": True})
    product = await _make_product_with_images(db, 3, wc_id=90002)

    await spin_ai_service.maybe_trigger(db, product, background=None)
    await db.commit()

    row = await db.scalar(select(Product).where(Product.id == product.id))
    assert row.spin_frames_json == []


@pytest.mark.asyncio
async def test_maybe_trigger_clears_stale_frames_when_disabled_later(db):
    await update_theme(db, {"product_360_enabled": True})
    product = await _make_product_with_images(db, 4, wc_id=90003)
    product.spin_frames_json = ["http://old/frame.webp"]
    await db.flush()

    await update_theme(db, {"product_360_enabled": False})
    await spin_ai_service.maybe_trigger(db, product, background=None)
    await db.commit()

    row = await db.scalar(select(Product).where(Product.id == product.id))
    assert row.spin_frames_json == []


@pytest.mark.asyncio
async def test_generate_spin_frames_uses_ai_only_for_similar_pairs(db, monkeypatch):
    """2 pares parecidos (similarity alta) + 1 par bem diferente (baixa) --
    só os pares parecidos ganham quadros de IA."""
    await update_theme(db, {"product_360_enabled": True})
    product = await _make_product_with_images(db, 4, wc_id=90004)
    await db.commit()

    calls: list[tuple[bytes, bytes]] = []

    def fake_similarity(b0: bytes, b1: bytes) -> float:
        calls.append((b0, b1))
        # só o par (índice 1, 2) é "parecido" -- os outros ficam abaixo do limiar
        return 0.95 if len(calls) == 2 else 0.5

    def fake_interpolate(b0: bytes, b1: bytes, n_frames: int) -> list[bytes]:
        return [b"quadro-gerado"] * n_frames

    monkeypatch.setattr(spin_ai_service, "foreground_similarity", fake_similarity)
    monkeypatch.setattr(spin_ai_service, "interpolate_between", fake_interpolate)

    product_id = product.id
    await spin_ai_service.generate_spin_frames(product_id)

    db.expire(product)  # a geração roda numa sessão própria; força reler do banco
    row = await db.scalar(select(Product).where(Product.id == product_id))
    # 4 fotos originais + 2 quadros gerados (só no par parecido) = 6
    assert len(row.spin_frames_json) == 6
    assert len(calls) == 3  # 3 pares adjacentes pra 4 fotos


@pytest.mark.asyncio
async def test_generate_spin_frames_noop_below_min_images(db):
    await update_theme(db, {"product_360_enabled": True})
    product = await _make_product_with_images(db, 2, wc_id=90005)
    await db.commit()

    product_id = product.id
    await spin_ai_service.generate_spin_frames(product_id)

    db.expire(product)
    row = await db.scalar(select(Product).where(Product.id == product_id))
    assert row.spin_frames_json == []


@pytest.mark.asyncio
async def test_generate_spin_frames_unknown_product_is_noop():
    await spin_ai_service.generate_spin_frames(uuid.uuid4())  # não deve levantar
