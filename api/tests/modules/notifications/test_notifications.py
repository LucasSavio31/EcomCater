"""Testes do módulo `notifications`: gate, criação via evento de pedido
(nova venda/novo envio) e as ações do sininho (ler, ler tudo, apagar,
apagar tudo)."""
from __future__ import annotations

import asyncio

import pytest

from app.modules.notifications import stream

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
    cat = (await client.post("/api/admin/categories", json={"name": "C"}, headers=h)).json()
    p = (
        await client.post(
            "/api/admin/products",
            json={"name": "Item", "category_id": cat["id"], "price_cents": 7000, "status": "active"},
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
            json={"sku": "IT-U", "option_value_ids": [vid], "stock_qty": 5},
            headers=h,
        )
    ).json()
    return v["id"]


async def _order(client, variant, email="c@test.example"):
    await client.post("/api/cart/items", json={"variant_id": variant, "quantity": 1})
    r = await client.post("/api/orders/checkout", json={"email": email, "shipping_address": ADDRESS})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_requires_admin(client):
    r = await client.get("/api/admin/notifications")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_order_created_generates_notification(client, admin_token, auth_headers, variant):
    h = auth_headers(admin_token)
    order = await _order(client, variant)

    r = await client.get("/api/admin/notifications", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["unread_count"] == 1
    item = data["items"][0]
    assert item["type"] == "order_created"
    assert order["number"] in item["title"]
    assert item["link_path"] == f"/pedidos/{order['number']}"
    assert item["read_at"] is None
    assert item["created_at"]
    assert "Cliente Teste" in item["message"]


@pytest.mark.asyncio
async def test_order_shipped_generates_notification(client, admin_token, auth_headers, variant):
    h = auth_headers(admin_token)
    order = await _order(client, variant)
    await client.post(f"/api/admin/orders/{order['number']}/status", json={"status": "paid"}, headers=h)
    await client.post(f"/api/admin/orders/{order['number']}/status", json={"status": "shipped"}, headers=h)

    data = (await client.get("/api/admin/notifications", headers=h)).json()
    types = [i["type"] for i in data["items"]]
    assert "order_created" in types
    assert "order_paid" in types
    assert "order_shipped" in types
    assert data["unread_count"] == 3


@pytest.mark.asyncio
async def test_order_paid_generates_notification_with_sound_flags(client, admin_token, auth_headers, variant):
    h = auth_headers(admin_token)
    order = await _order(client, variant)
    await client.post(f"/api/admin/orders/{order['number']}/status", json={"status": "paid"}, headers=h)

    data = (await client.get("/api/admin/notifications", headers=h)).json()
    types = [i["type"] for i in data["items"]]
    assert "order_paid" in types
    item = next(i for i in data["items"] if i["type"] == "order_paid")
    assert order["number"] in item["title"]
    assert data["sound_sale_enabled"] is True
    assert data["sound_return_enabled"] is True


@pytest.mark.asyncio
async def test_order_returned_generates_notification(client, admin_token, auth_headers, variant):
    h = auth_headers(admin_token)
    order = await _order(client, variant)
    await client.post(f"/api/admin/orders/{order['number']}/status", json={"status": "paid"}, headers=h)
    await client.post(f"/api/admin/orders/{order['number']}/status", json={"status": "returned"}, headers=h)

    data = (await client.get("/api/admin/notifications", headers=h)).json()
    types = [i["type"] for i in data["items"]]
    assert "order_returned" in types
    item = next(i for i in data["items"] if i["type"] == "order_returned")
    assert order["number"] in item["title"]


@pytest.mark.asyncio
async def test_sound_flags_reflect_theme_settings(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    r = await client.put(
        "/api/admin/theme",
        json={"sound_sale_enabled": False, "sound_return_enabled": False},
        headers=h,
    )
    assert r.status_code == 200, r.text

    data = (await client.get("/api/admin/notifications", headers=h)).json()
    assert data["sound_sale_enabled"] is False
    assert data["sound_return_enabled"] is False


@pytest.mark.asyncio
async def test_realtime_stream_publishes_on_order_paid_and_returned(client, admin_token, auth_headers, variant):
    """O sininho não pode depender só do polling de 30s -- confirma que o
    evento chega no `stream` (WebSocket) assim que o pedido é pago/devolvido."""
    h = auth_headers(admin_token)
    order = await _order(client, variant)

    q = stream.subscribe()
    try:
        await client.post(f"/api/admin/orders/{order['number']}/status", json={"status": "paid"}, headers=h)
        paid_event = await asyncio.wait_for(q.get(), timeout=5)
        assert paid_event["type"] == "order_paid"
        assert order["number"] in paid_event["title"]

        await client.post(f"/api/admin/orders/{order['number']}/status", json={"status": "returned"}, headers=h)
        returned_event = await asyncio.wait_for(q.get(), timeout=5)
        assert returned_event["type"] == "order_returned"
        assert order["number"] in returned_event["title"]
    finally:
        stream.unsubscribe(q)


@pytest.mark.asyncio
async def test_mark_read_and_mark_all_read(client, admin_token, auth_headers, variant):
    h = auth_headers(admin_token)
    await _order(client, variant)
    await _order(client, variant, email="c2@test.example")

    data = (await client.get("/api/admin/notifications", headers=h)).json()
    assert data["unread_count"] == 2
    first_id = data["items"][0]["id"]

    r = await client.post(f"/api/admin/notifications/{first_id}/read", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["read_at"] is not None

    data2 = (await client.get("/api/admin/notifications", headers=h)).json()
    assert data2["unread_count"] == 1

    all_read = await client.post("/api/admin/notifications/read-all", headers=h)
    assert all_read.status_code == 200

    data3 = (await client.get("/api/admin/notifications", headers=h)).json()
    assert data3["unread_count"] == 0


@pytest.mark.asyncio
async def test_delete_one_and_delete_all(client, admin_token, auth_headers, variant):
    h = auth_headers(admin_token)
    await _order(client, variant)
    await _order(client, variant, email="c2@test.example")

    data = (await client.get("/api/admin/notifications", headers=h)).json()
    assert len(data["items"]) == 2
    first_id = data["items"][0]["id"]

    r = await client.delete(f"/api/admin/notifications/{first_id}", headers=h)
    assert r.status_code == 200, r.text

    data2 = (await client.get("/api/admin/notifications", headers=h)).json()
    assert len(data2["items"]) == 1

    r2 = await client.delete("/api/admin/notifications", headers=h)
    assert r2.status_code == 200, r2.text

    data3 = (await client.get("/api/admin/notifications", headers=h)).json()
    assert data3["items"] == []
    assert data3["unread_count"] == 0
