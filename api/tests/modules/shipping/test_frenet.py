"""Testes do provedor Frenet (segundo provedor de frete, ao lado do Melhor
Envio). As chamadas HTTP reais (`httpx.AsyncClient`) são mockadas -- o
objetivo é a lógica de mapeamento/roteamento/fluxo, não a integração real.

Confere também que nada do Melhor Envio quebrou (o teste de
`test_reverse_logistics.py` já cobre isso à parte, roda 100% igual)."""
from __future__ import annotations

import httpx
import pytest

from app.core.errors import DomainError
from app.modules.shipping import service as shipping_service
from app.modules.shipping.providers.base import Package
from app.modules.shipping.providers.frenet import FrenetProvider
from app.modules.shipping.providers.melhor_envio import MelhorEnvioProvider

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
    cat = (await client.post("/api/admin/categories", json={"name": "F"}, headers=h)).json()
    p = (
        await client.post(
            "/api/admin/products",
            json={"name": "Item Frenet", "category_id": cat["id"], "price_cents": 8000, "status": "active"},
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
            json={"sku": "FR-U", "option_value_ids": [vid], "stock_qty": 5},
            headers=h,
        )
    ).json()
    return v["id"]


async def _order_with_frenet_rate(client, db, variant):
    from sqlalchemy import select

    from app.modules.orders.models import Order

    await client.post("/api/cart/items", json={"variant_id": variant, "quantity": 1})
    r = await client.post(
        "/api/orders/checkout", json={"email": "fr@test.example", "shipping_address": ADDRESS}
    )
    assert r.status_code == 201, r.text
    order = await db.scalar(select(Order).where(Order.number == r.json()["number"]))
    order.cpf = "11144477735"
    order.status = "paid"  # labels só saem pra pedido pago, mesma regra do ME
    order.shipping_service_json = {
        "id": "04014", "service": "SEDEX", "carrier": "Correios",
        "price_cents": 4200, "delivery_days": 2, "provider": "frenet",
        "extra": {"carrier_code": "04082"},
    }
    await db.flush()
    return order


async def _setup_config(db):
    await shipping_service.save_config(
        db,
        {
            "active_provider": "frenet",
            "frenet_token": "test-token",
            "frenet_partner_token": "test-partner-token",
            "origin_zip": "01001000",
            "sender_cpf": "11144477735",
        },
    )
    await db.flush()


# --------------------------------------------------------------------- cotação
@pytest.mark.asyncio
async def test_frenet_quote_maps_rates(monkeypatch):
    async def fake_post(self, url, json=None, **kwargs):
        assert url == "https://api.frenet.com.br/shipping/quote"
        assert kwargs["headers"]["token"] == "tok-123"
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "ShippingSevicesArray": [
                    {
                        "ServiceCode": "04014", "ServiceDescription": "SEDEX", "Carrier": "Correios",
                        "CarrierCode": "04082", "ShippingPrice": "42.00", "DeliveryTime": "2", "Error": False,
                    },
                    {
                        "ServiceCode": "04510", "ServiceDescription": "PAC", "Carrier": "Correios",
                        "CarrierCode": "04082", "ShippingPrice": "28.50", "DeliveryTime": "6", "Error": False,
                    },
                    {"ServiceCode": "X", "Error": True, "Msg": "sem cobertura"},
                ]
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    provider = FrenetProvider(token="tok-123")
    rates = await provider.quote(
        origin_zip="01001000", dest_zip="20040002",
        packages=[Package(weight_grams=500, length_mm=200, width_mm=150, height_mm=100, insurance_cents=8000)],
    )
    assert [r.id for r in rates] == ["04510", "04014"]  # ordenado por preço
    assert rates[0].price_cents == 2850
    assert rates[0].carrier == "Correios"
    assert rates[0].provider == "frenet"
    assert rates[0].extra == {"carrier_code": "04082"}


@pytest.mark.asyncio
async def test_frenet_quote_without_token_raises():
    provider = FrenetProvider(token="")
    with pytest.raises(DomainError, match="não configurado"):
        await provider.quote(origin_zip="01001000", dest_zip="20040002", packages=[Package(300, 200, 150, 100)])


@pytest.mark.asyncio
async def test_provider_factory_picks_frenet_when_active(db, monkeypatch):
    """`_provider()` escolhe a Frenet quando `active_provider="frenet"` --
    prova de que o roteamento genérico funciona sem tocar no branch do ME."""
    await _setup_config(db)
    cfg = await shipping_service.load_config(db)
    provider = shipping_service._provider(cfg)
    assert isinstance(provider, FrenetProvider)
    assert provider.token == "test-token"

    # e o ME continua funcionando quando é ele o ativo (comportamento
    # inalterado -- prova que o branch do ME não foi tocado)
    await shipping_service.save_config(db, {"active_provider": "melhor_envio", "melhor_envio_token": "me-tok"})
    cfg2 = await shipping_service.load_config(db)
    provider2 = shipping_service._provider(cfg2)
    assert isinstance(provider2, MelhorEnvioProvider)


# --------------------------------------------------------------------- webhook
def test_frenet_verify_webhook_fails_closed_without_config():
    provider = FrenetProvider(token="t")
    assert provider.verify_webhook({"x-minha-chave": "abc"}, b"{}") is False


def test_frenet_verify_webhook_checks_custom_header():
    provider = FrenetProvider(token="t", webhook_header_name="X-Minha-Chave", webhook_header_value="abc123")
    assert provider.verify_webhook({"x-minha-chave": "abc123"}, b"{}") is True
    assert provider.verify_webhook({"x-minha-chave": "errado"}, b"{}") is False


def test_frenet_parse_webhook_maps_event_type_to_status():
    provider = FrenetProvider(token="t")
    body = {
        "ShipmentId": 555,
        "TrackingNumber": "AA123456789BR",
        "TrackingEvents": [
            {"EventType": 0, "EventDateTime": "10/03/2026 09:00"},
            {"EventType": 1, "EventDateTime": "11/03/2026 14:00"},
        ],
    }
    update = provider.parse_webhook({}, body)
    assert update is not None
    assert update.provider_shipment_id == "555"
    assert update.tracking_code == "AA123456789BR"
    assert update.status == "EM_TRANSITO"  # último evento relevante da lista


def test_frenet_parse_webhook_ignores_unmapped_event():
    provider = FrenetProvider(token="t")
    body = {"ShipmentId": 1, "TrackingEvents": [{"EventType": 3}]}  # devolvido, sem mapa
    assert provider.parse_webhook({}, body) is None


# --------------------------------------------------------------------- etiqueta
@pytest.mark.asyncio
async def test_send_to_frenet_full_flow(client, db, variant, monkeypatch):
    order = await _order_with_frenet_rate(client, db, variant)
    await _setup_config(db)

    async def fake_post(self, url, json=None, **kwargs):
        assert kwargs["headers"]["x-partner-token"] == "test-partner-token"
        if url == "https://whitelabel.frenet.com.br/v1/shipments":
            assert isinstance(json, list) and json[0]["Quotation"]["ShippingServiceCode"] == "04014"
            return httpx.Response(200, json=[{"ShipmentId": 999}])
        if url == "https://whitelabel.frenet.com.br/v1/shipments/checkout":
            assert json == [999]
            return httpx.Response(200, json={"Status": 1})
        raise AssertionError(f"POST inesperado: {url}")

    async def fake_get(self, url, **kwargs):
        if url == "https://whitelabel.frenet.com.br/v1/shipments/999/label":
            return httpx.Response(
                200,
                json={
                    "ShipmentId": 999, "LabelUrl": "https://frenet.test/label/999.pdf",
                    "TrackingUrl": "https://frenet.test/track/999", "TrackingNumber": "AA999BR",
                },
            )
        raise AssertionError(f"GET inesperado: {url}")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = await shipping_service.send_orders_to_frenet(db, [order.number], buy=True)
    entry = result["results"][0]
    assert entry["ok"] is True
    assert entry["label_url"] == "https://frenet.test/label/999.pdf"
    assert entry["tracking_code"] == "AA999BR"

    await db.refresh(order)
    assert order.shipping_service_json["frenet_shipment_id"] == 999
    assert order.shipping_service_json["provider"] == "frenet"
    # não usa a chave do ME -- prova de que não colide com a rotina do ME
    assert "shipment_id" not in order.shipping_service_json
    assert order.status == "tracking_available"


@pytest.mark.asyncio
async def test_send_to_frenet_awaiting_payment_keeps_order_status(client, db, variant, monkeypatch):
    order = await _order_with_frenet_rate(client, db, variant)
    order.status = "paid"
    await db.flush()
    await _setup_config(db)

    async def fake_post(self, url, json=None, **kwargs):
        if url == "https://whitelabel.frenet.com.br/v1/shipments":
            return httpx.Response(200, json=[{"ShipmentId": 111}])
        if url == "https://whitelabel.frenet.com.br/v1/shipments/checkout":
            return httpx.Response(200, json={"Status": 2})  # aguardando pagamento
        raise AssertionError(f"POST inesperado: {url}")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await shipping_service.send_orders_to_frenet(db, [order.number], buy=True)
    entry = result["results"][0]
    assert entry["ok"] is True
    assert "aguardando" in entry["message"].lower() or "pendente" in entry["message"].lower()

    await db.refresh(order)
    assert order.shipping_service_json["frenet_tracking_status"] == "aguardando_pagamento"


@pytest.mark.asyncio
async def test_send_to_frenet_without_partner_token_reports_real_error(client, db, variant, monkeypatch):
    """Sem token de parceiro configurado: erro claro, não um crash cru --
    é o cenário mais provável (ver achado documentado no plano)."""
    order = await _order_with_frenet_rate(client, db, variant)
    await shipping_service.save_config(
        db,
        {
            "active_provider": "frenet", "frenet_token": "tok", "frenet_partner_token": "",
            "origin_zip": "01001000", "sender_cpf": "11144477735",
        },
    )
    await db.flush()

    result = await shipping_service.send_orders_to_frenet(db, [order.number], buy=True)
    entry = result["results"][0]
    assert entry["ok"] is False
    assert "parceiro" in entry["message"].lower() or "partner" in entry["message"].lower()


# --------------------------------------------------------------------- rastreio
@pytest.mark.asyncio
async def test_poll_frenet_tracking_advances_status(client, db, variant, monkeypatch):
    order = await _order_with_frenet_rate(client, db, variant)
    order.status = "processing"
    svc = dict(order.shipping_service_json)
    svc.update({"frenet_shipment_id": 777, "tracking_code": "AA777BR", "frenet_tracking_status": "criado"})
    order.shipping_service_json = svc
    await db.flush()
    await _setup_config(db)

    async def fake_post(self, url, json=None, **kwargs):
        assert url == "https://api.frenet.com.br/tracking/trackinginfo"
        assert json["TrackingNumber"] == "AA777BR"
        return httpx.Response(
            200,
            json={"TrackingEvents": [{"EventType": 9, "EventDateTime": "12/03/2026 10:00"}]},
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await shipping_service.poll_frenet_tracking(db)
    assert result["ran"] is True
    assert result["updated"] == 1

    await db.refresh(order)
    assert order.status == "delivered"
    assert order.shipping_service_json["frenet_tracking_status"] == "ENTREGUE"


@pytest.mark.asyncio
async def test_poll_frenet_tracking_does_not_pick_up_melhor_envio_orders(client, db, variant, monkeypatch):
    """Prova central da separação de chaves: um pedido do Melhor Envio (chave
    `shipment_id`) não deve nunca ser varrido pela rotina da Frenet."""
    order = await _order_with_frenet_rate(client, db, variant)
    order.shipping_service_json = {"shipment_id": "ME-123", "me_status": "cart"}
    await db.flush()
    await _setup_config(db)

    async def fake_post(self, url, json=None, **kwargs):
        raise AssertionError("rotina da Frenet não deveria chamar a API pra pedido do ME")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await shipping_service.poll_frenet_tracking(db)
    assert result == {"ran": True, "checked": 0, "updated": 0}


# --------------------------------------------------------------------- webhook end-to-end
@pytest.mark.asyncio
async def test_handle_frenet_tracking_webhook_updates_order(client, db, variant):
    order = await _order_with_frenet_rate(client, db, variant)
    order.status = "processing"
    svc = dict(order.shipping_service_json)
    svc["frenet_shipment_id"] = 42
    order.shipping_service_json = svc
    await db.flush()
    await shipping_service.save_config(
        db,
        {
            "frenet_token": "tok", "frenet_webhook_header_name": "X-Sig", "frenet_webhook_header_value": "secret1",
        },
    )
    await db.flush()

    result = await shipping_service.handle_frenet_tracking_webhook(
        db,
        {"x-sig": "secret1"},
        b"{}",
        {"ShipmentId": 42, "TrackingNumber": "AA42BR", "TrackingEvents": [{"EventType": 0}]},
    )
    assert result["matched"] is True
    assert result["status"] == "POSTADO"

    await db.refresh(order)
    assert order.shipping_service_json["tracking_code"] == "AA42BR"
    # POSTADO -> "shipped" (mesma régua de status do Melhor Envio)
    assert order.status == "shipped"
