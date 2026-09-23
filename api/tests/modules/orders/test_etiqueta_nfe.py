"""Etiqueta + NF-e numa página só ("Gerar Etq/NFe")."""
from __future__ import annotations

import io
from datetime import UTC, datetime

import pytest

ADDRESS = {
    "recipient_name": "Cliente Teste",
    "zip": "20040002",
    "street": "Av. Rio Branco",
    "number": "1",
    "district": "Centro",
    "city": "Rio de Janeiro",
    "state": "RJ",
}


@pytest.fixture
async def variant(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = (await client.post("/api/admin/categories", json={"name": "EtqNfe"}, headers=h)).json()
    p = (
        await client.post(
            "/api/admin/products",
            json={"name": "Item EtqNfe", "category_id": cat["id"], "price_cents": 7000, "status": "active"},
            headers=h,
        )
    ).json()
    await client.put(
        f"/api/admin/products/{p['id']}/option-types",
        json=[{"name": "T", "values": [{"value": "U"}]}],
        headers=h,
    )
    vid = (await client.get(f"/api/products/{p['slug']}")).json()["option_types"][0]["values"][0]["id"]
    v = (
        await client.post(
            f"/api/admin/products/{p['id']}/variants",
            json={"sku": "ETQNFE-U", "option_value_ids": [vid], "stock_qty": 5},
            headers=h,
        )
    ).json()
    return v["id"]


async def _order(client, variant, email):
    await client.post("/api/cart/items", json={"variant_id": variant, "quantity": 1})
    r = await client.post("/api/orders/checkout", json={"email": email, "shipping_address": ADDRESS})
    assert r.status_code == 201, r.text
    return r.json()


def _fake_label_pdf(n_pages: int = 1) -> bytes:
    """PDF real e pequeno (parseável pelo pypdf), do tamanho aproximado de
    uma etiqueta 10x15 -- substitui o render real do Melhor Envio/Playwright."""
    from weasyprint import HTML

    pages = "".join(
        '<div style="page-break-after: always; width:90mm; height:140mm;">'
        f"FAKE LABEL {i}</div>"
        for i in range(n_pages)
    )
    html = f'<html><head><style>@page {{ size: 100mm 150mm; margin:5mm; }}</style></head><body>{pages}</body></html>'
    return HTML(string=html).write_pdf()


async def _add_authorized_nfe(db, order_id, order_number, *, numero=54821, serie=4, chave=None) -> None:
    import uuid

    import app.modules.admin.models  # noqa: F401 - registra AdminUser pro FK resolver
    from app.modules.nfe.models import NfeDocument

    chave = chave or "35260900000000000000550001000000001000000001"
    db.add(
        NfeDocument(
            order_id=uuid.UUID(order_id) if isinstance(order_id, str) else order_id,
            order_number=order_number,
            status="authorized",
            ambiente="homologacao",
            numero=numero,
            serie=serie,
            chave_acesso=chave,
            total_cents=7000,
            authorized_at=datetime(2026, 8, 22, 14, 30, tzinfo=UTC),
        )
    )
    await db.flush()


def _clear_cache(order_number: str) -> None:
    """Garante que o teste não herde cache de uma rodada anterior (o cache
    fica no storage privado de verdade, não é resetado por teste)."""
    from app.modules.orders.etiqueta_nfe import _cache_key, _cache_meta_key
    from app.shared.storage import private_storage

    for key in (_cache_key(order_number), _cache_meta_key(order_number)):
        if private_storage.exists(key):
            private_storage.delete(key)


@pytest.mark.asyncio
async def test_etiqueta_nfe_stacks_strip_below_label_same_width(client, db, variant, monkeypatch):
    """A tarja fica empilhada embaixo da etiqueta, na MESMA largura dela --
    a etiqueta fica intocada (não encolhe), a página só fica mais alta."""
    from pypdf import PdfReader

    from app.modules.orders import etiqueta_nfe
    from app.modules.shipping import service as shipping_service

    order = await _order(client, variant, "etqnfe1@test.example")
    _clear_cache(order["number"])
    await _add_authorized_nfe(db, order["id"], order["number"])

    async def fake_pages(db_, numbers):
        return _fake_label_pdf(n_pages=len(numbers))

    monkeypatch.setattr(shipping_service, "melhor_envio_label_pages_for_nfe_merge", fake_pages)

    pdf = await etiqueta_nfe.build_etiqueta_nfe_pdf(db, [order["number"]])
    reader = PdfReader(io.BytesIO(pdf))
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    assert "54821" in text
    assert "Remessa" in text
    assert "DOCUMENTO FISCAL" in text
    # página mais alta que só a etiqueta (a tarja foi empilhada embaixo),
    # mas na MESMA largura da etiqueta nativa (nunca mais larga/estreita)
    label_only = PdfReader(io.BytesIO(_fake_label_pdf(1))).pages[0]
    assert float(reader.pages[0].mediabox.height) > float(label_only.mediabox.height)
    assert float(reader.pages[0].mediabox.width) == pytest.approx(float(label_only.mediabox.width), rel=0.01)


@pytest.mark.asyncio
async def test_etiqueta_nfe_keeps_plain_label_when_no_authorized_nfe(client, db, variant, monkeypatch):
    from pypdf import PdfReader

    from app.modules.orders import etiqueta_nfe
    from app.modules.shipping import service as shipping_service

    order = await _order(client, variant, "etqnfe2@test.example")
    _clear_cache(order["number"])
    # sem NF-e nenhuma pra este pedido

    async def fake_pages(db_, numbers):
        return _fake_label_pdf(n_pages=len(numbers))

    monkeypatch.setattr(shipping_service, "melhor_envio_label_pages_for_nfe_merge", fake_pages)

    pdf = await etiqueta_nfe.build_etiqueta_nfe_pdf(db, [order["number"]])
    reader = PdfReader(io.BytesIO(pdf))
    label_only = PdfReader(io.BytesIO(_fake_label_pdf(1))).pages[0]
    assert len(reader.pages) == 1
    # sem tarja -- altura igual à etiqueta pura (não cresceu)
    assert float(reader.pages[0].mediabox.height) == pytest.approx(float(label_only.mediabox.height), rel=0.01)
    assert "DOCUMENTO FISCAL" not in reader.pages[0].extract_text()


@pytest.mark.asyncio
async def test_etiqueta_nfe_bulk_mixed_orders(client, db, variant, monkeypatch):
    """Lote com um pedido COM NF-e e outro SEM -- cada página se comporta
    de acordo com o próprio pedido, sem travar o lote inteiro."""
    from pypdf import PdfReader

    from app.modules.orders import etiqueta_nfe
    from app.modules.shipping import service as shipping_service

    with_nfe = await _order(client, variant, "etqnfe3@test.example")
    without_nfe = await _order(client, variant, "etqnfe4@test.example")
    _clear_cache(with_nfe["number"])
    _clear_cache(without_nfe["number"])
    await _add_authorized_nfe(db, with_nfe["id"], with_nfe["number"], chave="35260900000000000000550001000000002000000002")

    async def fake_pages(db_, numbers):
        return _fake_label_pdf(n_pages=len(numbers))

    monkeypatch.setattr(shipping_service, "melhor_envio_label_pages_for_nfe_merge", fake_pages)

    pdf = await etiqueta_nfe.build_etiqueta_nfe_pdf(db, [with_nfe["number"], without_nfe["number"]])
    reader = PdfReader(io.BytesIO(pdf))
    assert len(reader.pages) == 2
    assert "DOCUMENTO FISCAL" in reader.pages[0].extract_text()
    assert "DOCUMENTO FISCAL" not in reader.pages[1].extract_text()


@pytest.mark.asyncio
async def test_etiqueta_nfe_caches_rendered_page_for_six_hours(client, db, variant, monkeypatch):
    """A segunda chamada pro mesmo pedido não deve renderizar de novo (o
    render via Melhor Envio/Playwright é caro) -- serve do cache."""
    from pypdf import PdfReader

    from app.modules.orders import etiqueta_nfe
    from app.modules.shipping import service as shipping_service

    order = await _order(client, variant, "etqnfe5@test.example")
    _clear_cache(order["number"])

    calls = {"n": 0}

    async def fake_pages(db_, numbers):
        calls["n"] += 1
        return _fake_label_pdf(n_pages=len(numbers))

    monkeypatch.setattr(shipping_service, "melhor_envio_label_pages_for_nfe_merge", fake_pages)

    pdf1 = await etiqueta_nfe.build_etiqueta_nfe_pdf(db, [order["number"]])
    assert calls["n"] == 1
    pdf2 = await etiqueta_nfe.build_etiqueta_nfe_pdf(db, [order["number"]])
    assert calls["n"] == 1  # não renderizou de novo -- veio do cache
    assert PdfReader(io.BytesIO(pdf1)).pages[0].extract_text() == PdfReader(io.BytesIO(pdf2)).pages[0].extract_text()

    _clear_cache(order["number"])


@pytest.mark.asyncio
async def test_etiqueta_nfe_cache_expires_after_ttl(client, db, variant, monkeypatch):
    from datetime import UTC, datetime, timedelta

    from app.modules.orders import etiqueta_nfe

    order = await _order(client, variant, "etqnfe6@test.example")
    _clear_cache(order["number"])
    etiqueta_nfe._write_cache(order["number"], b"%PDF-1.4 cached")

    # simula um cache de mais de 6h atrás
    import json

    from app.shared.storage import private_storage

    stale = json.dumps(
        {"generated_at": (datetime.now(UTC) - timedelta(hours=7)).isoformat()}
    ).encode("utf-8")
    private_storage.save(etiqueta_nfe._cache_meta_key(order["number"]), stale, content_type="application/json")

    assert etiqueta_nfe._read_cached_page(order["number"]) is None
    _clear_cache(order["number"])


@pytest.mark.asyncio
async def test_etiqueta_nfe_route_requires_auth(client):
    r = await client.get("/api/admin/orders/etiqueta-nfe", params={"numbers": "2026-000001"})
    assert r.status_code == 401
