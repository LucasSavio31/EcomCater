"""Testes de logística reversa (devolução) via Melhor Envio.

As chamadas HTTP reais pro Melhor Envio (`httpx.AsyncClient.post`) e a
cotação (`MelhorEnvioProvider.quote`) são mockadas — o objetivo aqui é a
lógica do fluxo (carrinho -> checkout -> gera -> PDF -> status do pedido),
não a integração real (já validada manualmente contra o Sandbox nesta
sessão)."""
from __future__ import annotations

import httpx
import pytest

from app.core.errors import DomainError
from app.modules.shipping import service as shipping_service
from app.modules.shipping.providers.base import ShippingRate
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


async def _delivered_order(client, db, variant):
    await client.post("/api/cart/items", json={"variant_id": variant, "quantity": 1})
    r = await client.post(
        "/api/orders/checkout", json={"email": "c@test.example", "shipping_address": ADDRESS}
    )
    assert r.status_code == 201, r.text
    number = r.json()["number"]

    from sqlalchemy import select

    from app.modules.orders.models import Order

    order = await db.scalar(select(Order).where(Order.number == number))
    order.cpf = "11144477735"
    order.status = "delivered"
    await db.flush()
    return order


async def _setup_config(db):
    await shipping_service.save_config(
        db,
        {
            "melhor_envio_token": "test-token",
            "melhor_envio_sandbox": True,
            "origin_zip": "01001000",
            "sender_cpf": "11144477735",
        },
    )
    await db.flush()


def _patch_quote(monkeypatch):
    async def fake_quote(self, *, origin_zip, dest_zip, packages):
        return [
            ShippingRate(id="3", service=".Package", carrier="Jadlog", price_cents=1500, delivery_days=5)
        ]

    monkeypatch.setattr(MelhorEnvioProvider, "quote", fake_quote)


def _patch_render(monkeypatch):
    async def fake_render(url, *, postal_card, want_declaration):
        return b"%PDF-1.4 fake reverse label"

    monkeypatch.setattr(shipping_service, "_render_url_to_pdf", fake_render)


@pytest.mark.asyncio
async def test_reverse_label_success(client, db, variant, monkeypatch):
    order = await _delivered_order(client, db, variant)
    await _setup_config(db)
    _patch_quote(monkeypatch)
    _patch_render(monkeypatch)

    async def fake_post(self, url, json=None, **kwargs):
        if url.endswith("/api/v2/me/cart"):
            return httpx.Response(201, json={"id": "SHIP-REV-1"})
        if url.endswith("/api/v2/me/shipment/checkout"):
            return httpx.Response(200, json={"purchase": {"protocol": "PUR-TEST-1"}})
        if url.endswith("/api/v2/me/shipment/generate"):
            return httpx.Response(200, json={})
        if url.endswith("/api/v2/me/shipment/print"):
            return httpx.Response(
                200, json={"url": "https://sandbox.melhorenvio.com.br/imprimir/test"}
            )
        if url.endswith("/api/v2/me/shipment/tracking"):
            return httpx.Response(200, json={"SHIP-REV-1": {"tracking": "TRACKTEST123"}})
        raise AssertionError(f"POST inesperado: {url}")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await shipping_service.generate_reverse_label(db, order.number)
    assert result["ok"] is True
    assert result["label_pdf"] is True
    assert result["tracking_code"] == "TRACKTEST123"
    assert result["reverse_label_key"] == f"orders/{order.number}/reverse-label.pdf"

    await db.refresh(order)
    assert order.status == "returning"
    assert order.reverse_shipping_json["reverse_label_key"]
    # nunca mexe no envio de ida
    assert order.shipping_service_json in (None, {})

    from app.shared.storage import private_storage

    pdf = private_storage.read(order.reverse_shipping_json["reverse_label_key"])
    assert pdf == b"%PDF-1.4 fake reverse label"


@pytest.mark.asyncio
async def test_reverse_label_no_balance_keeps_status(client, db, variant, monkeypatch):
    order = await _delivered_order(client, db, variant)
    await _setup_config(db)
    _patch_quote(monkeypatch)

    async def fake_post(self, url, json=None, **kwargs):
        if url.endswith("/api/v2/me/cart"):
            return httpx.Response(201, json={"id": "SHIP-REV-2"})
        if url.endswith("/api/v2/me/shipment/checkout"):
            return httpx.Response(
                422, json={"message": "Seu saldo é insuficiente para o pagamento"}
            )
        raise AssertionError(f"POST inesperado: {url}")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await shipping_service.generate_reverse_label(db, order.number)
    assert result["ok"] is True
    assert result["awaiting_payment"] is True

    # a função em si só marca no objeto em memória (como o `_me_label_for_order`
    # do envio de ida já faz) -- quem persiste é o commit de fim de request
    # (`get_db()`), simulado aqui.
    await db.commit()
    await db.refresh(order)
    assert order.status == "delivered"  # não avança sem a etiqueta sair de fato
    assert order.reverse_shipping_json["me_status"] == "awaiting_me_payment"


@pytest.mark.asyncio
async def test_reverse_label_guards(client, db, variant, monkeypatch):
    order = await _delivered_order(client, db, variant)
    await _setup_config(db)

    # sem CPF válido
    order.cpf = None
    order.shipping_address_json = {**ADDRESS}
    await db.flush()
    with pytest.raises(DomainError):
        await shipping_service.generate_reverse_label(db, order.number)

    # endereço incompleto
    order.cpf = "11144477735"
    order.shipping_address_json = {**ADDRESS, "street": ""}
    await db.flush()
    with pytest.raises(DomainError):
        await shipping_service.generate_reverse_label(db, order.number)

    # já tem logística reversa
    order.shipping_address_json = {**ADDRESS}
    order.reverse_shipping_json = {"shipment_id": "already-there"}
    await db.flush()
    with pytest.raises(DomainError):
        await shipping_service.generate_reverse_label(db, order.number)


@pytest.mark.asyncio
async def test_sync_reverse_tracking_advances_status_automatically(client, db, variant, monkeypatch):
    """returning -> return_posted -> returned, tudo automático via rastreio
    dos Correios (mockado) -- nunca precisa de confirmação manual."""
    order = await _delivered_order(client, db, variant)
    order.status = "returning"
    order.reverse_shipping_json = {"shipment_id": "SHIP-SYNC-1"}
    await db.flush()
    await _setup_config(db)

    async def fake_post(self, url, json=None, **kwargs):
        if url.endswith("/api/v2/me/shipment/tracking"):
            return httpx.Response(200, json={"SHIP-SYNC-1": {}})
        raise AssertionError(f"POST inesperado: {url}")

    async def fake_get(self, url, **kwargs):
        if url.endswith("/api/v2/me/orders/SHIP-SYNC-1"):
            return httpx.Response(200, json={"status": "posted", "posted_at": "2026-01-01 10:00:00"})
        raise AssertionError(f"GET inesperado: {url}")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = await shipping_service.sync_reverse_tracking(db)
    assert result["ran"] is True
    await db.refresh(order)
    assert order.status == "return_posted"

    # segunda rodada: Correios confirmam entrega -> vira "returned" direto
    async def fake_get_delivered(self, url, **kwargs):
        return httpx.Response(
            200, json={"status": "delivered", "delivered_at": "2026-01-02 09:00:00"}
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get_delivered)

    result2 = await shipping_service.sync_reverse_tracking(db)
    assert result2["ran"] is True
    await db.refresh(order)
    assert order.status == "returned"
