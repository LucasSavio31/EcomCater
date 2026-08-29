"""Testes do módulo `products` — CRUD, variações, listagem/filtros, busca, reviews."""
from __future__ import annotations

import pytest


async def _mk_category(client, h, name="Feminino", parent_id=None):
    body = {"name": name}
    if parent_id:
        body["parent_id"] = parent_id
    return (await client.post("/api/admin/categories", json=body, headers=h)).json()


async def _mk_product(client, h, cat_id, name="Vestido Longo Floral", price=12990, status="active"):
    r = await client.post(
        "/api/admin/products",
        json={"name": name, "category_id": cat_id, "price_cents": price, "status": status},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_product_crud_and_slug(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = await _mk_category(client, h)
    p = await _mk_product(client, h, cat["id"])
    assert p["slug"] == "vestido-longo-floral"

    detail = await client.get(f"/api/products/{p['slug']}")
    assert detail.status_code == 200
    assert detail.json()["price_cents"] == 12990
    assert detail.json()["breadcrumb"][0]["name"] == "Home"


@pytest.mark.asyncio
async def test_draft_not_public(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = await _mk_category(client, h)
    p = await _mk_product(client, h, cat["id"], name="Rascunho", status="draft")
    assert (await client.get(f"/api/products/{p['slug']}")).status_code == 404


@pytest.mark.asyncio
async def test_variants_and_size_option(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = await _mk_category(client, h)
    p = await _mk_product(client, h, cat["id"])

    ot = await client.put(
        f"/api/admin/products/{p['id']}/option-types",
        json=[{"name": "Numeração", "is_size": True, "values": [{"value": "38"}, {"value": "40"}]}],
        headers=h,
    )
    assert ot.status_code == 200

    detail = await client.get(f"/api/products/{p['slug']}")
    val_ids = [v["id"] for v in detail.json()["option_types"][0]["values"]]

    v1 = await client.post(
        f"/api/admin/products/{p['id']}/variants",
        json={"sku": "VLF-38", "option_value_ids": [val_ids[0]], "stock_qty": 5},
        headers=h,
    )
    assert v1.status_code == 201
    v2 = await client.post(
        f"/api/admin/products/{p['id']}/variants",
        json={"sku": "VLF-40", "option_value_ids": [val_ids[1]], "stock_qty": 0},
        headers=h,
    )
    assert v2.status_code == 201

    detail = (await client.get(f"/api/products/{p['slug']}")).json()
    stock = {v["sku"]: v["in_stock"] for v in detail["variants"]}
    assert stock == {"VLF-38": True, "VLF-40": False}


@pytest.mark.asyncio
async def test_duplicate_sku_rejected(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = await _mk_category(client, h)
    p = await _mk_product(client, h, cat["id"])
    await client.put(
        f"/api/admin/products/{p['id']}/option-types",
        json=[{"name": "Cor", "values": [{"value": "Preto"}]}],
        headers=h,
    )
    vid = (await client.get(f"/api/products/{p['slug']}")).json()["option_types"][0]["values"][0]["id"]
    a = await client.post(
        f"/api/admin/products/{p['id']}/variants",
        json={"sku": "DUP", "option_value_ids": [vid], "stock_qty": 1},
        headers=h,
    )
    assert a.status_code == 201
    b = await client.post(
        f"/api/admin/products/{p['id']}/variants",
        json={"sku": "DUP", "option_value_ids": [vid], "stock_qty": 1},
        headers=h,
    )
    assert b.status_code == 409


@pytest.mark.asyncio
async def test_list_by_category_and_price_filter(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    top = await _mk_category(client, h, "Masculino")
    sub = await _mk_category(client, h, "Camisetas", parent_id=top["id"])
    await _mk_product(client, h, sub["id"], name="Camiseta Barata", price=5000)
    await _mk_product(client, h, sub["id"], name="Camiseta Cara", price=20000)

    all_in_top = await client.get("/api/products", params={"category": "masculino"})
    assert all_in_top.status_code == 200
    assert all_in_top.json()["total"] == 2  # inclui subcategoria

    cheap = await client.get(
        "/api/products", params={"category": "masculino/camisetas", "price_max": 9999}
    )
    names = [i["name"] for i in cheap.json()["items"]]
    assert names == ["Camiseta Barata"]


@pytest.mark.asyncio
async def test_search_fuzzy(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = await _mk_category(client, h)
    await _mk_product(client, h, cat["id"], name="Vestido Midi Preto")
    res = await client.get("/api/products/search", params={"q": "vestid"})
    assert res.status_code == 200
    assert any(r["type"] == "product" and "Vestido" in r["name"] for r in res.json())


@pytest.mark.asyncio
async def test_review_flow(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = await _mk_category(client, h)
    p = await _mk_product(client, h, cat["id"])

    r = await client.post(
        f"/api/products/{p['slug']}/reviews",
        json={"author_name": "Maria", "rating": 5, "title": "Amei", "body": "Perfeito"},
    )
    assert r.status_code == 201
    review_id = r.json()["id"]

    # ainda não aparece (pending)
    detail = (await client.get(f"/api/products/{p['slug']}")).json()
    assert detail["reviews"] == []
    assert detail["rating_count"] == 0

    mod = await client.post(
        f"/api/admin/products/{p['id']}/reviews/{review_id}/moderate",
        json={"status": "approved"},
        headers=h,
    )
    assert mod.status_code == 200

    detail = (await client.get(f"/api/products/{p['slug']}")).json()
    assert detail["rating_count"] == 1
    assert detail["rating_avg"] == 5.0
