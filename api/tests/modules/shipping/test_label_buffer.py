"""Buffer local de etiquetas do Melhor Envio (1h) -- evita reabrir a página
deles num navegador headless a cada clique dentro da janela."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.modules.shipping import label_buffer
from app.modules.shipping import service as shipping_service

ADDRESS = {
    "recipient_name": "Cliente Teste",
    "zip": "20040002",
    "street": "Av. Rio Branco",
    "number": "1",
    "district": "Centro",
    "city": "Rio de Janeiro",
    "state": "RJ",
}


def _clear_all():
    label_buffer.clear_buffer()


@pytest.fixture(autouse=True)
def _isolate_buffer():
    _clear_all()
    yield
    _clear_all()


def test_compute_key_stable_and_order_independent():
    a = label_buffer.compute_key(["2026-000002", "2026-000001"], "termica_10x15", False)
    b = label_buffer.compute_key(["2026-000001", "2026-000002"], "termica_10x15", False)
    assert a == b  # ordem dos pedidos não importa


def test_compute_key_differs_by_format_or_declaration():
    base = label_buffer.compute_key(["2026-000001"], "termica_10x15", False)
    diff_fmt = label_buffer.compute_key(["2026-000001"], "a4_4up", False)
    diff_decl = label_buffer.compute_key(["2026-000001"], "termica_10x15", True)
    assert base != diff_fmt
    assert base != diff_decl


def test_write_read_roundtrip():
    key = label_buffer.compute_key(["2026-000001"], "termica_10x15", False)
    assert label_buffer.read_buffer(key) is None
    label_buffer.write_buffer(key, b"%PDF-1.4 fake")
    assert label_buffer.read_buffer(key) == b"%PDF-1.4 fake"


def test_buffer_expires_after_ttl():
    import json

    from app.shared.storage import private_storage

    key = label_buffer.compute_key(["2026-000001"], "termica_10x15", False)
    label_buffer.write_buffer(key, b"%PDF-1.4 fake")

    stale = json.dumps(
        {"generated_at": (datetime.now(UTC) - timedelta(hours=2)).isoformat()}
    ).encode("utf-8")
    private_storage.save(label_buffer._meta_key(key), stale, content_type="application/json")

    assert label_buffer.read_buffer(key) is None


def test_clear_buffer_removes_all_entries():
    k1 = label_buffer.compute_key(["2026-000001"], "termica_10x15", False)
    k2 = label_buffer.compute_key(["2026-000002"], "termica_10x15", False)
    label_buffer.write_buffer(k1, b"%PDF-1.4 a")
    label_buffer.write_buffer(k2, b"%PDF-1.4 b")

    removed = label_buffer.clear_buffer()
    assert removed >= 2
    assert label_buffer.read_buffer(k1) is None
    assert label_buffer.read_buffer(k2) is None


@pytest.fixture
async def variant(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = (await client.post("/api/admin/categories", json={"name": "Buf"}, headers=h)).json()
    p = (
        await client.post(
            "/api/admin/products",
            json={"name": "Item Buf", "category_id": cat["id"], "price_cents": 7000, "status": "active"},
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
            json={"sku": "BUF-U", "option_value_ids": [vid], "stock_qty": 5},
            headers=h,
        )
    ).json()
    return v["id"]


async def _order_with_shipment(client, db, variant, email):
    await client.post("/api/cart/items", json={"variant_id": variant, "quantity": 1})
    r = await client.post("/api/orders/checkout", json={"email": email, "shipping_address": ADDRESS})
    assert r.status_code == 201, r.text
    number = r.json()["number"]

    from sqlalchemy import select

    from app.modules.orders.models import Order

    order = await db.scalar(select(Order).where(Order.number == number))
    order.shipping_service_json = {"shipment_id": f"SHIP-{number}"}
    await db.flush()
    return order


async def _setup_config(db):
    await shipping_service.save_config(
        db,
        {
            "melhor_envio_token": "test-token",
            "melhor_envio_sandbox": True,
            "origin_zip": "01001000",
            "sender_cpf": "11144477735",
        },
    )
    await db.flush()


@pytest.mark.asyncio
async def test_melhor_envio_labels_pdf_uses_buffer_on_second_call(client, db, variant, monkeypatch):
    order = await _order_with_shipment(client, db, variant, "buf1@test.example")
    await _setup_config(db)

    async def fake_post(self, url, json=None, **kwargs):
        if url.endswith("/api/v2/me/shipment/generate"):
            return httpx.Response(200, json={})
        if url.endswith("/api/v2/me/shipment/print"):
            return httpx.Response(200, json={"url": "https://sandbox.melhorenvio.com.br/imprimir/test"})
        raise AssertionError(f"POST inesperado: {url}")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    calls = {"n": 0}

    async def fake_render(url, *, postal_card, want_declaration):
        calls["n"] += 1
        return b"%PDF-1.4 fake label render"

    monkeypatch.setattr(shipping_service, "_render_url_to_pdf", fake_render)

    pdf1 = await shipping_service.melhor_envio_labels_pdf(db, [order.number])
    assert calls["n"] == 1
    pdf2 = await shipping_service.melhor_envio_labels_pdf(db, [order.number])
    assert calls["n"] == 1  # segunda chamada veio do buffer, não renderizou de novo
    assert pdf1 == pdf2

    # limpar o buffer força renderizar de novo
    label_buffer.clear_buffer()
    pdf3 = await shipping_service.melhor_envio_labels_pdf(db, [order.number])
    assert calls["n"] == 2
    assert pdf3 == b"%PDF-1.4 fake label render"


@pytest.mark.asyncio
async def test_clear_labels_buffer_route(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    key = label_buffer.compute_key(["2026-000001"], "termica_10x15", False)
    label_buffer.write_buffer(key, b"%PDF-1.4 fake")

    r = await client.post("/api/admin/orders/labels-buffer/clear", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    assert r.json()["removed"] >= 2  # blob + meta
    assert label_buffer.read_buffer(key) is None


@pytest.mark.asyncio
async def test_clear_labels_buffer_route_requires_auth(client):
    r = await client.post("/api/admin/orders/labels-buffer/clear")
    assert r.status_code == 401
