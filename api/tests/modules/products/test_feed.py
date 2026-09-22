"""Testes do feed do Google Merchant Center (`GET /api/products/feed/google-merchant.xml`)."""
from __future__ import annotations

import io
from xml.etree import ElementTree as ET

import pytest
from PIL import Image

_G_NS = "http://base.google.com/ns/1.0"


def _g(tag: str) -> str:
    return f"{{{_G_NS}}}{tag}"


def _png_bytes() -> bytes:
    im = Image.new("RGB", (200, 200), (200, 120, 40))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


async def _mk_category(client, h, name="Calçados"):
    return (await client.post("/api/admin/categories", json={"name": name}, headers=h)).json()


async def _mk_product(client, h, cat_id, **kwargs):
    body = {"name": "Bota Feed Teste", "category_id": cat_id, "price_cents": 19990, "status": "active"}
    body.update(kwargs)
    r = await client.post("/api/admin/products", json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


async def _upload_image(client, h, product_id):
    files = {"file": ("foto.png", _png_bytes(), "image/png")}
    r = await client.post(f"/api/admin/products/{product_id}/images", files=files, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_feed_is_valid_xml_with_google_namespace(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = await _mk_category(client, h)
    p = await _mk_product(client, h, cat["id"])
    await _upload_image(client, h, p["id"])

    r = await client.get("/api/products/feed/google-merchant.xml")
    assert r.status_code == 200, r.text
    assert "xml" in r.headers["content-type"]

    root = ET.fromstring(r.content)
    assert root.tag == "rss"
    channel = root.find("channel")
    assert channel is not None
    items = channel.findall("item")
    assert len(items) == 1

    item = items[0]
    assert item.find(_g("id")).text
    assert item.find(_g("item_group_id")).text == p["id"]
    assert item.find("title").text
    assert item.find("link").text.endswith(f"/produto/{p['slug']}")
    assert item.find(_g("image_link")).text
    assert item.find(_g("availability")).text == "in stock"
    assert item.find(_g("price")).text == "199.90 BRL"
    assert item.find(_g("condition")).text == "new"
    assert item.find(_g("brand")).text


@pytest.mark.asyncio
async def test_feed_skips_product_without_image(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = await _mk_category(client, h)
    await _mk_product(client, h, cat["id"], name="Sem Foto")

    r = await client.get("/api/products/feed/google-merchant.xml")
    root = ET.fromstring(r.content)
    items = root.find("channel").findall("item")
    assert len(items) == 0


@pytest.mark.asyncio
async def test_feed_omits_draft_and_archived_products(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = await _mk_category(client, h)
    draft = await _mk_product(client, h, cat["id"], name="Rascunho", status="draft")
    await _upload_image(client, h, draft["id"])
    archived = await _mk_product(client, h, cat["id"], name="Arquivado", status="archived")
    await _upload_image(client, h, archived["id"])

    r = await client.get("/api/products/feed/google-merchant.xml")
    root = ET.fromstring(r.content)
    items = root.find("channel").findall("item")
    assert len(items) == 0


@pytest.mark.asyncio
async def test_feed_lists_each_variant_grouped_by_item_group_id(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = await _mk_category(client, h)
    p = await _mk_product(client, h, cat["id"])
    await _upload_image(client, h, p["id"])

    await client.put(
        f"/api/admin/products/{p['id']}/option-types",
        json=[{"name": "Numeração", "values": [{"value": "38"}, {"value": "39"}]}],
        headers=h,
    )
    detail = (await client.get(f"/api/products/{p['slug']}")).json()
    values = detail["option_types"][0]["values"]
    v38, v39 = values[0]["id"], values[1]["id"]

    await client.post(
        f"/api/admin/products/{p['id']}/variants",
        json={"sku": "FEED-38", "option_value_ids": [v38], "stock_qty": 5},
        headers=h,
    )
    await client.post(
        f"/api/admin/products/{p['id']}/variants",
        json={"sku": "FEED-39", "option_value_ids": [v39], "stock_qty": 0},
        headers=h,
    )

    r = await client.get("/api/products/feed/google-merchant.xml")
    root = ET.fromstring(r.content)
    items = root.find("channel").findall("item")
    assert len(items) == 2
    group_ids = {item.find(_g("item_group_id")).text for item in items}
    assert group_ids == {p["id"]}
    availabilities = sorted(item.find(_g("availability")).text for item in items)
    assert availabilities == ["in stock", "out of stock"]
    titles = sorted(item.find("title").text for item in items)
    assert titles == ["Bota Feed Teste - 38", "Bota Feed Teste - 39"]


@pytest.mark.asyncio
async def test_feed_uses_gtin_when_barcode_present(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = await _mk_category(client, h)
    p = await _mk_product(client, h, cat["id"])
    await _upload_image(client, h, p["id"])

    r = await client.post(
        f"/api/admin/products/{p['id']}/variants",
        json={"sku": "FEED-GTIN", "option_value_ids": [], "stock_qty": 3, "barcode": "7891234567895"},
        headers=h,
    )
    assert r.status_code == 201, r.text

    feed_r = await client.get("/api/products/feed/google-merchant.xml")
    root = ET.fromstring(feed_r.content)
    item = root.find("channel").find("item")
    assert item.find(_g("gtin")).text == "7891234567895"
    assert item.find(_g("mpn")) is None
    assert item.find(_g("identifier_exists")) is None


@pytest.mark.asyncio
async def test_feed_uses_mpn_and_identifier_exists_no_without_barcode(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = await _mk_category(client, h)
    p = await _mk_product(client, h, cat["id"])
    await _upload_image(client, h, p["id"])

    r = await client.get("/api/products/feed/google-merchant.xml")
    root = ET.fromstring(r.content)
    item = root.find("channel").find("item")
    assert item.find(_g("gtin")) is None
    assert item.find(_g("mpn")).text
    assert item.find(_g("identifier_exists")).text == "no"
