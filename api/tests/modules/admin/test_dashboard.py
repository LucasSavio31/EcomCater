"""Dashboard admin: top 10 estados e relatório em PDF."""
from __future__ import annotations

import pytest

ADDRESS_SP = {
    "recipient_name": "Cliente SP",
    "zip": "01310200",
    "street": "Av. Paulista",
    "number": "1",
    "district": "Bela Vista",
    "city": "São Paulo",
    "state": "SP",
}


@pytest.fixture
async def variant_dash(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = (await client.post("/api/admin/categories", json={"name": "Dash"}, headers=h)).json()
    p = (
        await client.post(
            "/api/admin/products",
            json={"name": "Item Dash", "category_id": cat["id"], "price_cents": 5000, "status": "active"},
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
            json={"sku": "DASH-U", "option_value_ids": [vid], "stock_qty": 5},
            headers=h,
        )
    ).json()
    return v["id"]


async def _paid_order(client, h, variant, email):
    await client.post("/api/cart/items", json={"variant_id": variant, "quantity": 1})
    r = await client.post(
        "/api/orders/checkout", json={"email": email, "shipping_address": ADDRESS_SP}
    )
    assert r.status_code == 201, r.text
    order = r.json()
    await client.post(
        f"/api/admin/orders/{order['number']}/status", json={"status": "paid"}, headers=h
    )
    return order


@pytest.mark.asyncio
async def test_dashboard_includes_top_states(client, variant_dash, admin_token, auth_headers):
    h = auth_headers(admin_token)
    await _paid_order(client, h, variant_dash, "dashsp1@test.example")
    await _paid_order(client, h, variant_dash, "dashsp2@test.example")

    r = await client.get("/api/admin/dashboard", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    sp = next((s for s in body["top_states"] if s["state"] == "SP"), None)
    assert sp is not None
    assert sp["orders"] >= 2
    assert sp["revenue_cents"] >= 10000


@pytest.mark.asyncio
async def test_dashboard_report_pdf_downloads(client, variant_dash, admin_token, auth_headers):
    h = auth_headers(admin_token)
    await _paid_order(client, h, variant_dash, "dashpdf@test.example")

    r = await client.get("/api/admin/dashboard/report.pdf", headers=h)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"]
    assert r.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_dashboard_report_pdf_requires_admin(client):
    r = await client.get("/api/admin/dashboard/report.pdf")
    assert r.status_code == 401
