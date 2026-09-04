"""Cobrança + webhook do módulo `payment`.

Cobre a arquitetura assíncrona do checkout:
- cartão recusado retorna erro HTTP (não passa como sucesso pro cliente);
- `order.payment_status` reflete a recusa (não fica "pending" pra sempre);
- webhook idempotente (mesmo evento 2x não duplica) e resiliente a corrida
  (duas entregas quase simultâneas do MESMO evento);
- e-mail/fatura (SMTP/PDF) não impedem a resposta rápida do endpoint.
"""
from __future__ import annotations

import asyncio

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

CARD_OK = {
    "number": "4111 1111 1111 1111",
    "holder_name": "Cliente Teste",
    "exp_month": 12,
    "exp_year": 2030,
    "cvv": "123",
    "installments": 1,
}

CARD_DECLINED = {**CARD_OK, "number": "4111 1111 1111 0000"}  # FakeGateway recusa terminando em 0000


@pytest.fixture
async def fake_gateway(client, admin_token, auth_headers):
    """Liga o gateway `fake` (sem credenciais reais) pro módulo payment."""
    h = auth_headers(admin_token)
    r = await client.put("/api/admin/payment/config", json={"active_provider": "fake"}, headers=h)
    assert r.status_code == 200, r.text
    return h


@pytest.fixture
async def variant(client, admin_token, auth_headers, fake_gateway):
    h = auth_headers(admin_token)
    cat = (await client.post("/api/admin/categories", json={"name": "Pay"}, headers=h)).json()
    p = (
        await client.post(
            "/api/admin/products",
            json={"name": "Item Pay", "category_id": cat["id"], "price_cents": 7000, "status": "active"},
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
            json={"sku": "PAY-U", "option_value_ids": [vid], "stock_qty": 5},
            headers=h,
        )
    ).json()
    return v["id"]


async def _order(client, variant, email):
    await client.post("/api/cart/items", json={"variant_id": variant, "quantity": 1})
    r = await client.post("/api/orders/checkout", json={"email": email, "shipping_address": ADDRESS})
    assert r.status_code == 201, r.text
    return r.json()


async def _charge(client, order_number, method="credit_card", card=None):
    return await client.post(
        "/api/payment/charge",
        json={"order_number": order_number, "method": method, "card": card},
    )


@pytest.mark.asyncio
async def test_card_approved_marks_order_paid_without_blocking_on_email(client, variant):
    order = await _order(client, variant, "pay1@test.example")
    r = await _charge(client, order["number"], "credit_card", CARD_OK)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "paid"

    got = await client.get(f"/api/orders/{order['number']}", params={"email": "pay1@test.example"})
    # `finalize_paid` encadeia pending_payment -> paid -> processing na hora
    assert got.json()["status"] == "processing"
    assert got.json()["payment_status"] == "paid"


@pytest.mark.asyncio
async def test_card_declined_returns_error_and_does_not_look_like_success(client, variant):
    """Antes: recusa vinha em HTTP 200 (`status: "failed"` no corpo) — o front só
    olha `response.ok`, então o cliente caía na tela de obrigado achando que
    tinha pago. Agora tem que vir HTTP != 2xx."""
    order = await _order(client, variant, "pay2@test.example")
    r = await _charge(client, order["number"], "credit_card", CARD_DECLINED)
    assert r.status_code == 402, r.text  # PaymentError

    # o pedido não fica preso em "pending" pra sempre — cancela e o
    # payment_status reflete a recusa (não "pending" indefinidamente).
    got = await client.get(f"/api/orders/{order['number']}", params={"email": "pay2@test.example"})
    body = got.json()
    assert body["status"] == "canceled"
    assert body["payment_status"] == "failed"

    status_res = await client.get(f"/api/payment/status/{order['number']}")
    assert status_res.json()["payment_status"] == "failed"


@pytest.mark.asyncio
async def test_pix_charge_pending_then_webhook_confirms(client, variant):
    order = await _order(client, variant, "pay3@test.example")
    r = await _charge(client, order["number"], "pix")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pending"
    assert r.json()["pix_qr_code"]

    got = await client.get(f"/api/orders/{order['number']}", params={"email": "pay3@test.example"})
    assert got.json()["status"] == "pending_payment"

    wh = await client.post(
        "/api/webhooks/payment/fake",
        json={"event_id": "evt-pix-1", "order_number": order["number"], "status": "paid"},
    )
    assert wh.status_code == 200, wh.text
    assert wh.json()["matched"] is True

    got = await client.get(f"/api/orders/{order['number']}", params={"email": "pay3@test.example"})
    assert got.json()["status"] == "processing"
    assert got.json()["payment_status"] == "paid"


@pytest.mark.asyncio
async def test_webhook_same_event_twice_is_idempotent(client, variant, admin_token, auth_headers):
    h = auth_headers(admin_token)
    order = await _order(client, variant, "pay4@test.example")
    await _charge(client, order["number"], "pix")

    payload = {"event_id": "evt-dup-1", "order_number": order["number"], "status": "paid"}
    r1 = await client.post("/api/webhooks/payment/fake", json=payload)
    r2 = await client.post("/api/webhooks/payment/fake", json=payload)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r2.json().get("duplicate") is True

    # não duplicou o financial_event: só 1 fato "paid" (7000) no livro-caixa
    summary = (await client.get("/api/admin/financial/summary", headers=h)).json()
    assert summary["gross_cents"] == 7000


@pytest.mark.asyncio
async def test_webhook_race_same_event_concurrently_does_not_500(client, variant):
    """Duas entregas do MESMO evento quase ao mesmo tempo (retry agressivo do
    gateway): a constraint de idempotência pode colidir no flush — não pode
    estourar 500 pro gateway, tem que resolver como duplicado."""
    order = await _order(client, variant, "pay5@test.example")
    await _charge(client, order["number"], "pix")

    payload = {"event_id": "evt-race-1", "order_number": order["number"], "status": "paid"}
    r1, r2 = await asyncio.gather(
        client.post("/api/webhooks/payment/fake", json=payload),
        client.post("/api/webhooks/payment/fake", json=payload),
    )
    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text

    got = await client.get(f"/api/orders/{order['number']}", params={"email": "pay5@test.example"})
    assert got.json()["status"] == "processing"
    assert got.json()["payment_status"] == "paid"


@pytest.mark.asyncio
async def test_refund_marks_order_refunded(client, variant, admin_token, auth_headers):
    h = auth_headers(admin_token)
    order = await _order(client, variant, "pay6@test.example")
    await _charge(client, order["number"], "credit_card", CARD_OK)

    r = await client.post(f"/api/admin/payment/refund/{order['number']}", json={}, headers=h)
    assert r.status_code == 200, r.text

    got = await client.get(f"/api/orders/{order['number']}", params={"email": "pay6@test.example"})
    assert got.json()["status"] == "refunded"
    assert got.json()["payment_status"] == "refunded"
