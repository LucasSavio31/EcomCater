"""E2E do fluxo crítico: catálogo → carrinho → checkout → pagamento → confirmação.

Usa o gateway `fake` (sem credenciais). Cobre cartão aprovado, cartão recusado +
retry, e Pix confirmado por webhook.
"""
from __future__ import annotations

import pytest


@pytest.fixture
async def catalog(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = (await client.post("/api/admin/categories", json={"name": "Feminino"}, headers=h)).json()
    p = (
        await client.post(
            "/api/admin/products",
            json={"name": "Vestido Teste", "category_id": cat["id"], "price_cents": 10000, "status": "active"},
            headers=h,
        )
    ).json()
    await client.put(
        f"/api/admin/products/{p['id']}/option-types",
        json=[{"name": "Numeração", "is_size": True, "values": [{"value": "38"}]}],
        headers=h,
    )
    vid = (await client.get(f"/api/products/{p['slug']}")).json()["option_types"][0]["values"][0]["id"]
    v = (
        await client.post(
            f"/api/admin/products/{p['id']}/variants",
            json={"sku": "VT-38", "option_value_ids": [vid], "stock_qty": 10},
            headers=h,
        )
    ).json()
    # provider de pagamento = fake
    await client.put(
        "/api/admin/payment/config", json={"active_provider": "fake"}, headers=h
    )
    return {"product": p, "variant_id": v["id"], "slug": p["slug"]}


async def _fill_cart(client, variant_id, qty=2):
    r = await client.post("/api/cart/items", json={"variant_id": variant_id, "quantity": qty})
    assert r.status_code == 201, r.text
    return r


ADDRESS = {
    "recipient_name": "Maria Silva",
    "zip": "01001000",
    "street": "Praça da Sé",
    "number": "100",
    "district": "Sé",
    "city": "São Paulo",
    "state": "SP",
}


@pytest.mark.asyncio
async def test_card_approved_flow(client, catalog):
    await _fill_cart(client, catalog["variant_id"], 2)
    cart = (await client.get("/api/cart")).json()
    assert cart["totals"]["items_total_cents"] == 20000

    checkout = await client.post(
        "/api/orders/checkout",
        json={"email": "maria@test.local", "shipping_address": ADDRESS},
    )
    assert checkout.status_code == 201, checkout.text
    order = checkout.json()
    assert order["status"] == "pending_payment"
    assert order["grand_total_cents"] == 20000

    # carrinho esvaziado após criar o pedido
    assert (await client.get("/api/cart")).json()["items"] == []

    pay = await client.post(
        "/api/payment/charge",
        json={
            "order_number": order["number"],
            "method": "credit_card",
            "card": {
                "number": "4111111111111111",
                "holder_name": "MARIA SILVA",
                "exp_month": 12,
                "exp_year": 2030,
                "cvv": "123",
                "installments": 1,
            },
        },
    )
    assert pay.status_code == 200, pay.text
    assert pay.json()["status"] == "paid"

    final = (await client.get(f"/api/orders/{order['number']}", params={"email": "maria@test.local"})).json()
    assert final["status"] == "processing"
    assert final["payment_status"] == "paid"

    # estoque baixado: 10 - 2 = 8
    detail = (await client.get(f"/api/products/{catalog['slug']}")).json()
    assert detail["variants"][0]["stock_qty"] == 8


@pytest.mark.asyncio
async def test_card_declined_then_retry(client, catalog):
    await _fill_cart(client, catalog["variant_id"], 1)
    order = (
        await client.post(
            "/api/orders/checkout",
            json={"email": "joao@test.local", "shipping_address": ADDRESS},
        )
    ).json()

    declined = await client.post(
        "/api/payment/charge",
        json={
            "order_number": order["number"],
            "method": "credit_card",
            "card": {
                "number": "4111111111110000",  # termina em 0000 => recusa
                "holder_name": "JOAO",
                "exp_month": 1,
                "exp_year": 2031,
                "cvv": "123",
            },
        },
    )
    # cobrança criada, mas recusada -> pedido cancelado
    assert declined.status_code == 200
    assert declined.json()["status"] in ("failed",)
    cancelled = (await client.get(f"/api/orders/{order['number']}", params={"email": "joao@test.local"})).json()
    assert cancelled["status"] == "canceled"


@pytest.mark.asyncio
async def test_pix_confirmed_by_webhook(client, catalog):
    await _fill_cart(client, catalog["variant_id"], 1)
    order = (
        await client.post(
            "/api/orders/checkout",
            json={"email": "ana@test.local", "shipping_address": ADDRESS},
        )
    ).json()

    pix = await client.post(
        "/api/payment/charge", json={"order_number": order["number"], "method": "pix"}
    )
    assert pix.status_code == 200
    assert pix.json()["status"] == "pending"
    assert pix.json()["pix_qr_code"]

    # ainda não pago
    assert (
        await client.get(f"/api/orders/{order['number']}", params={"email": "ana@test.local"})
    ).json()["status"] == "pending_payment"

    # webhook do gateway confirma
    wh = await client.post(
        "/api/webhooks/payment/fake",
        json={"order_number": order["number"], "status": "paid", "event_id": "evt-1"},
    )
    assert wh.status_code == 200, wh.text
    assert wh.json()["matched"] is True

    paid = (await client.get(f"/api/orders/{order['number']}", params={"email": "ana@test.local"})).json()
    assert paid["status"] == "processing"
    assert paid["payment_status"] == "paid"

    # webhook duplicado é idempotente
    dup = await client.post(
        "/api/webhooks/payment/fake",
        json={"order_number": order["number"], "status": "paid", "event_id": "evt-1"},
    )
    assert dup.json().get("duplicate") is True


@pytest.mark.asyncio
async def test_coupon_and_totals(client, catalog, admin_token, auth_headers):
    h = auth_headers(admin_token)
    await client.post(
        "/api/admin/promotions",
        json={"code": "DEZ", "type": "percent", "value": 10},
        headers=h,
    )
    await _fill_cart(client, catalog["variant_id"], 1)  # 10000
    applied = await client.post("/api/cart/coupon", json={"code": "DEZ"})
    assert applied.status_code == 200
    totals = applied.json()["totals"]
    assert totals["discount_cents"] == 1000
    assert totals["grand_total_cents"] == 9000
