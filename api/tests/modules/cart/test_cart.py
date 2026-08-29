"""Testes do módulo `cart` — persistência por cookie, estoque, snapshot, merge."""
from __future__ import annotations

import pytest


@pytest.fixture
async def variant(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = (await client.post("/api/admin/categories", json={"name": "Cat"}, headers=h)).json()
    p = (
        await client.post(
            "/api/admin/products",
            json={"name": "Produto X", "category_id": cat["id"], "price_cents": 5000, "status": "active"},
            headers=h,
        )
    ).json()
    await client.put(
        f"/api/admin/products/{p['id']}/option-types",
        json=[{"name": "Cor", "values": [{"value": "Azul"}]}],
        headers=h,
    )
    vid = (await client.get(f"/api/products/{p['slug']}")).json()["option_types"][0]["values"][0]["id"]
    v = (
        await client.post(
            f"/api/admin/products/{p['id']}/variants",
            json={"sku": "PX-AZ", "option_value_ids": [vid], "stock_qty": 3},
            headers=h,
        )
    ).json()
    return v["id"]


@pytest.mark.asyncio
async def test_add_and_persist_via_cookie(client, variant):
    r = await client.post("/api/cart/items", json={"variant_id": variant, "quantity": 2})
    assert r.status_code == 201
    assert "cart_token" in r.cookies or r.json()["token"]

    again = await client.get("/api/cart")
    assert again.json()["totals"]["items_count"] == 2
    assert again.json()["totals"]["items_total_cents"] == 10000


@pytest.mark.asyncio
async def test_stock_limit_enforced(client, variant):
    r = await client.post("/api/cart/items", json={"variant_id": variant, "quantity": 5})
    assert r.status_code == 422
    assert "estoque" in r.text.lower()


@pytest.mark.asyncio
async def test_update_and_remove_item(client, variant):
    await client.post("/api/cart/items", json={"variant_id": variant, "quantity": 1})
    cart = (await client.get("/api/cart")).json()
    item_id = cart["items"][0]["id"]

    upd = await client.patch(f"/api/cart/items/{item_id}", json={"quantity": 3})
    assert upd.json()["totals"]["items_count"] == 3

    rem = await client.patch(f"/api/cart/items/{item_id}", json={"quantity": 0})
    assert rem.json()["items"] == []


@pytest.mark.asyncio
async def test_price_snapshot_and_change_flag(client, variant, admin_token, auth_headers):
    await client.post("/api/cart/items", json={"variant_id": variant, "quantity": 1})
    # muda o preço do produto
    h = auth_headers(admin_token)
    detail = None
    # descobre o product_id via listagem admin
    plist = (await client.get("/api/admin/products", headers=h)).json()["items"]
    pid = plist[0]["id"]
    await client.patch(f"/api/admin/products/{pid}", json={"price_cents": 9999}, headers=h)

    cart = (await client.get("/api/cart")).json()
    assert cart["items"][0]["unit_price_cents"] == 5000  # snapshot mantido
    assert cart["items"][0]["price_changed"] is True
