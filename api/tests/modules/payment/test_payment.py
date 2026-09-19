"""Cobrança + webhook do módulo `payment`.

Cobre a arquitetura assíncrona do checkout:
- cartão recusado retorna erro HTTP (não passa como sucesso pro cliente);
- `order.payment_status` reflete a recusa (não fica "pending" pra sempre);
- webhook idempotente (mesmo evento 2x não duplica) e resiliente a corrida
  (duas entregas quase simultâneas do MESMO evento);
- e-mail/fatura (SMTP/PDF) não impedem a resposta rápida do endpoint;
- arquitetura de provedores (`providers` + `method_providers`): cadastro/
  liga-desliga de cada provedor separado do vínculo método -> provedor,
  migração do formato antigo sem perder credenciais reais, webhook resolvido
  pelo provedor da própria URL e reembolso pelo provedor que processou o
  pagamento (não pelo vínculo atual do método).
"""
from __future__ import annotations

import asyncio

import pytest

from app.modules.payment import service

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
    """Liga o provedor `fake` (sem credenciais reais) e vincula os 3 métodos
    a ele -- os dois eixos separados da arquitetura nova (provider on/off +
    vínculo método -> provider)."""
    h = auth_headers(admin_token)
    r = await client.put("/api/admin/payment/config/providers/fake", json={"enabled": True}, headers=h)
    assert r.status_code == 200, r.text
    r = await client.put(
        "/api/admin/payment/config/method-providers",
        json={"credit_card": "fake", "pix": "fake", "boleto": "fake"},
        headers=h,
    )
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


# --------------------------- arquitetura de provedores --------------------------- #


def test_migrate_legacy_config_preserves_appmax_credentials():
    """A migração é o ponto mais arriscado do refactor -- roda em cima da
    config REAL da loja em produção (token/segredo reais do Appmax). Perder
    um desses na primeira leitura pós-deploy quebraria pagamento ao vivo."""
    raw = {
        "active_provider": "appmax",
        "appmax_access_token": "TESTE-0000-1111-2222-3333",
        "appmax_sandbox": False,
        "appmax_webhook_secret": "whsec-teste-123",
        "methods": {"credit_card": True, "pix": True, "boleto": False},
        "max_installments": 6,
    }
    migrated = service._migrate_legacy_config(raw)

    appmax = migrated["providers"]["appmax"]
    assert appmax["enabled"] is True
    assert appmax["config"]["access_token"] == "TESTE-0000-1111-2222-3333"
    assert appmax["config"]["sandbox"] is False
    assert appmax["config"]["webhook_secret"] == "whsec-teste-123"
    assert migrated["method_providers"] == {"credit_card": "appmax", "pix": "appmax"}
    assert migrated["max_installments"] == 6

    # idempotente: já migrado, não mexe de novo
    assert service._migrate_legacy_config(migrated) == migrated


def test_migrate_legacy_config_noop_for_fresh_or_empty_config():
    assert service._migrate_legacy_config({}) == {}
    already_new = {"providers": {"fake": {"enabled": True, "config": {}}}, "method_providers": {}}
    assert service._migrate_legacy_config(already_new) == already_new


@pytest.mark.asyncio
async def test_get_config_and_update_provider_credentials(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    r = await client.get("/api/admin/payment/config", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body["providers"]) >= {"appmax", "fake"}

    r = await client.put(
        "/api/admin/payment/config/providers/appmax",
        json={"enabled": True, "config": {"access_token": "tok-1", "sandbox": True}},
        headers=h,
    )
    assert r.status_code == 200, r.text
    appmax_out = r.json()["providers"]["appmax"]
    assert appmax_out["enabled"] is True
    assert appmax_out["has_token"] is True
    # segredo nunca volta em texto puro no GET
    assert "access_token" not in appmax_out

    # provedor desconhecido -> erro de validação, não 500
    r = await client.put("/api/admin/payment/config/providers/stripe", json={"enabled": True}, headers=h)
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_update_method_providers_replaces_whole_mapping(client, fake_gateway, admin_token, auth_headers):
    h = auth_headers(admin_token)
    r = await client.put(
        "/api/admin/payment/config/method-providers",
        json={"credit_card": "fake", "pix": None, "boleto": None, "max_installments": 3},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["method_providers"] == {"credit_card": "fake"}
    assert r.json()["max_installments"] == 3

    methods = (await client.get("/api/payment/methods")).json()
    assert methods["credit_card"] is True
    assert methods["pix"] is False
    assert methods["boleto"] is False
    assert methods["max_installments"] == 3


@pytest.mark.asyncio
async def test_webhook_resolves_gateway_by_url_provider_not_method_providers(
    client, variant, admin_token, auth_headers
):
    """Correção real: antes o webhook usava o "provedor ativo" global; agora
    usa o provedor da PRÓPRIA URL do webhook. Prova disso: desvincula `pix`
    de `fake` (nenhum método aponta mais pra ele) e confirma que o webhook em
    `/api/webhooks/payment/fake` ainda funciona."""
    h = auth_headers(admin_token)
    order = await _order(client, variant, "pay-wh-1@test.example")
    await _charge(client, order["number"], "pix")

    r = await client.put(
        "/api/admin/payment/config/method-providers",
        json={"credit_card": None, "pix": None, "boleto": None},
        headers=h,
    )
    assert r.status_code == 200, r.text

    wh = await client.post(
        "/api/webhooks/payment/fake",
        json={"event_id": "evt-url-slug-1", "order_number": order["number"], "status": "paid"},
    )
    assert wh.status_code == 200, wh.text
    assert wh.json()["matched"] is True

    got = await client.get(f"/api/orders/{order['number']}", params={"email": "pay-wh-1@test.example"})
    assert got.json()["payment_status"] == "paid"


@pytest.mark.asyncio
async def test_refund_uses_payment_provider_not_current_method_providers(
    client, variant, admin_token, auth_headers
):
    """Correção real: reembolso usa o provedor QUE PROCESSOU o pagamento
    (gravado em `payment.provider`), não o vínculo atual do método -- podem
    ter mudado entre a cobrança e o reembolso."""
    h = auth_headers(admin_token)
    order = await _order(client, variant, "pay-refund-1@test.example")
    await _charge(client, order["number"], "credit_card", CARD_OK)

    r = await client.put(
        "/api/admin/payment/config/method-providers",
        json={"credit_card": None, "pix": None, "boleto": None},
        headers=h,
    )
    assert r.status_code == 200, r.text

    r = await client.post(f"/api/admin/payment/refund/{order['number']}", json={}, headers=h)
    assert r.status_code == 200, r.text

    got = await client.get(f"/api/orders/{order['number']}", params={"email": "pay-refund-1@test.example"})
    assert got.json()["payment_status"] == "refunded"
