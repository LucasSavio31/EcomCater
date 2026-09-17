"""Testes do módulo `woocommerce`: a loja respondendo como um WooCommerce
de verdade em `/wp-json/wc/v3/...` -- autenticação, pedidos, produtos/
variações e webhooks (entrega mockada, nunca bate em rede real)."""
from __future__ import annotations

import base64
import hashlib
import hmac

import pytest

from app.modules.woocommerce import service as woo_service

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
    cat = (await client.post("/api/admin/categories", json={"name": "Botas"}, headers=h)).json()
    p = (
        await client.post(
            "/api/admin/products",
            json={"name": "Item", "category_id": cat["id"], "price_cents": 7000, "status": "active"},
            headers=h,
        )
    ).json()
    await client.put(
        f"/api/admin/products/{p['id']}/option-types",
        json=[{"name": "Numeração", "values": [{"value": "40"}]}],
        headers=h,
    )
    vid = (await client.get(f"/api/products/{p['slug']}")).json()["option_types"][0]["values"][0]["id"]
    v = (
        await client.post(
            f"/api/admin/products/{p['id']}/variants",
            json={"sku": "IT-40", "option_value_ids": [vid], "stock_qty": 5},
            headers=h,
        )
    ).json()
    return {"product_id": p["id"], "variant_id": v["id"]}


async def _order(client, variant_id, email="c@test.example"):
    await client.post("/api/cart/items", json={"variant_id": variant_id, "quantity": 1})
    r = await client.post("/api/orders/checkout", json={"email": email, "shipping_address": ADDRESS})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
async def wc_key(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    r = await client.post(
        "/api/admin/woocommerce/keys", json={"description": "Bling", "permission": "read_write"}, headers=h
    )
    assert r.status_code == 200, r.text
    return r.json()


# ------------------------------------------------------------------- auth

@pytest.mark.asyncio
async def test_orders_require_auth(client):
    r = await client.get("/wp-json/wc/v3/orders")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_invalid_credentials_rejected(client):
    r = await client.get("/wp-json/wc/v3/orders", auth=("ck_bogus", "cs_bogus"))
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_read_only_key_cannot_write(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    key = (
        await client.post(
            "/api/admin/woocommerce/keys", json={"description": "Leitura", "permission": "read"}, headers=h
        )
    ).json()
    r = await client.put(
        "/wp-json/wc/v3/orders/1",
        json={"status": "processing"},
        auth=(key["consumer_key"], key["consumer_secret"]),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_query_string_auth_also_works(client, wc_key):
    r = await client.get(
        "/wp-json/wc/v3/orders",
        params={"consumer_key": wc_key["consumer_key"], "consumer_secret": wc_key["consumer_secret"]},
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_root_discovery(client):
    r = await client.get("/wp-json")
    assert r.status_code == 200, r.text
    assert "wc/v3" in r.json()["namespaces"]


# ----------------------------------------------------------------- pedidos

@pytest.mark.asyncio
async def test_order_appears_in_wc_shape(client, variant, wc_key):
    order = await _order(client, variant["variant_id"])
    auth = (wc_key["consumer_key"], wc_key["consumer_secret"])

    listed = await client.get("/wp-json/wc/v3/orders", auth=auth)
    assert listed.status_code == 200, listed.text
    assert listed.headers["x-wp-total"] == "1"
    wc_order = listed.json()[0]
    assert wc_order["status"] == "pending"
    assert wc_order["number"] == order["number"]
    assert not wc_order["order_key"].startswith("wc")
    assert wc_order["billing"]["postcode"] == "20040002"
    assert wc_order["line_items"][0]["sku"] == "IT-40"

    single = await client.get(f"/wp-json/wc/v3/orders/{wc_order['id']}", auth=auth)
    assert single.status_code == 200
    assert single.json()["id"] == wc_order["id"]


@pytest.mark.asyncio
async def test_wc_status_update_reuses_our_transition_side_effects(
    client, variant, wc_key, admin_token, auth_headers
):
    """PUT status=cancelled precisa devolver estoque -- prova que a escrita
    passa pelo `orders.service.transition` de verdade, não um shortcut."""
    order = await _order(client, variant["variant_id"])
    auth = (wc_key["consumer_key"], wc_key["consumer_secret"])
    wc_order = (await client.get("/wp-json/wc/v3/orders", auth=auth)).json()[0]

    r = await client.put(
        f"/wp-json/wc/v3/orders/{wc_order['id']}", json={"status": "cancelled"}, auth=auth
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"

    h = auth_headers(admin_token)
    detail = (await client.get(f"/api/admin/orders/{order['number']}", headers=h)).json()
    assert detail["status"] == "canceled"

    slug = (await client.get("/api/products?category=botas")).json()["items"][0]["slug"]
    stock = (await client.get(f"/api/products/{slug}")).json()["variants"][0]["stock_qty"]
    assert stock == 5  # devolvido


@pytest.mark.asyncio
async def test_wc_tracking_meta_saves_on_order(client, variant, wc_key):
    await _order(client, variant["variant_id"])
    auth = (wc_key["consumer_key"], wc_key["consumer_secret"])
    wc_order = (await client.get("/wp-json/wc/v3/orders", auth=auth)).json()[0]

    r = await client.put(
        f"/wp-json/wc/v3/orders/{wc_order['id']}",
        json={"meta_data": [{"key": "_tracking_number", "value": "BR123456789"}]},
        auth=auth,
    )
    assert r.status_code == 200, r.text

    single = await client.get(f"/wp-json/wc/v3/orders/{wc_order['id']}", auth=auth)
    assert single.status_code == 200


# ---------------------------------------------------------------- produtos

@pytest.mark.asyncio
async def test_product_and_variation_shape(client, variant, wc_key):
    auth = (wc_key["consumer_key"], wc_key["consumer_secret"])
    products = await client.get("/wp-json/wc/v3/products", auth=auth)
    assert products.status_code == 200, products.text
    wc_product = next(p for p in products.json() if p["sku"] or p["variations"])
    assert wc_product["type"] == "variable"
    assert len(wc_product["variations"]) == 1

    variations = await client.get(f"/wp-json/wc/v3/products/{wc_product['id']}/variations", auth=auth)
    assert variations.status_code == 200, variations.text
    v = variations.json()[0]
    assert v["sku"] == "IT-40"
    assert v["stock_quantity"] == 5
    assert v["attributes"] == [{"name": "Numeração", "option": "40"}]


@pytest.mark.asyncio
async def test_variation_stock_update_reflects_in_store(client, variant, wc_key):
    auth = (wc_key["consumer_key"], wc_key["consumer_secret"])
    products = await client.get("/wp-json/wc/v3/products", auth=auth)
    wc_product = next(p for p in products.json() if p["variations"])
    variation_id = wc_product["variations"][0]

    r = await client.put(
        f"/wp-json/wc/v3/products/{wc_product['id']}/variations/{variation_id}",
        json={"stock_quantity": 42},
        auth=auth,
    )
    assert r.status_code == 200, r.text
    assert r.json()["stock_quantity"] == 42

    detail = await client.get("/api/products?category=botas")
    slug = detail.json()["items"][0]["slug"]
    pdp = (await client.get(f"/api/products/{slug}")).json()
    assert pdp["variants"][0]["stock_qty"] == 42


# --------------------------------------------------------------- webhooks

@pytest.mark.asyncio
async def test_register_and_list_webhook(client, wc_key):
    auth = (wc_key["consumer_key"], wc_key["consumer_secret"])
    r = await client.post(
        "/wp-json/wc/v3/webhooks",
        json={"topic": "order.created", "delivery_url": "https://bling.com.br/hook/abc", "secret": "s3gr3d0"},
        auth=auth,
    )
    assert r.status_code == 200, r.text
    hook = r.json()
    assert hook["topic"] == "order.created"

    listed = await client.get("/wp-json/wc/v3/webhooks", auth=auth)
    assert len(listed.json()) == 1

    deleted = await client.delete(f"/wp-json/wc/v3/webhooks/{hook['id']}", auth=auth)
    assert deleted.status_code == 200
    assert (await client.get("/wp-json/wc/v3/webhooks", auth=auth)).json() == []


@pytest.mark.asyncio
async def test_webhook_rejects_unknown_topic(client, wc_key):
    auth = (wc_key["consumer_key"], wc_key["consumer_secret"])
    r = await client.post(
        "/wp-json/wc/v3/webhooks",
        json={"topic": "product.created", "delivery_url": "https://x.example/hook"},
        auth=auth,
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_order_paid_delivers_webhook(client, variant, wc_key, admin_token, auth_headers, monkeypatch):
    auth = (wc_key["consumer_key"], wc_key["consumer_secret"])
    await client.post(
        "/wp-json/wc/v3/webhooks",
        json={"topic": "order.updated", "delivery_url": "https://bling.example/hook", "secret": "topsecret"},
        auth=auth,
    )

    delivered: list[dict] = []

    class _FakeResp:
        status_code = 200

    class _FakeAsyncClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, *, content, headers):
            delivered.append({"url": url, "content": content, "headers": headers})
            return _FakeResp()

    monkeypatch.setattr(woo_service.httpx, "AsyncClient", _FakeAsyncClient)

    order = await _order(client, variant["variant_id"])
    h = auth_headers(admin_token)
    r = await client.post(f"/api/admin/orders/{order['number']}/status", json={"status": "paid"}, headers=h)
    assert r.status_code == 200, r.text

    assert len(delivered) == 1
    call = delivered[0]
    assert call["url"] == "https://bling.example/hook"
    assert call["headers"]["X-WC-Webhook-Topic"] == "order.updated"
    expected_sig = base64.b64encode(
        hmac.new(b"topsecret", call["content"], hashlib.sha256).digest()
    ).decode()
    assert call["headers"]["X-WC-Webhook-Signature"] == expected_sig


# ------------------------------------------------------------------ chaves

@pytest.mark.asyncio
async def test_admin_key_management_requires_admin(client):
    r = await client.get("/api/admin/woocommerce/keys")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_key_secret_shown_once(client, wc_key, admin_token, auth_headers):
    h = auth_headers(admin_token)
    listed = (await client.get("/api/admin/woocommerce/keys", headers=h)).json()
    assert len(listed) == 1
    assert "consumer_secret" not in listed[0]
    assert listed[0]["consumer_key"] == wc_key["consumer_key"]
