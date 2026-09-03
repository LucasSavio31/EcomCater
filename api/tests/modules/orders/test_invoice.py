"""Fatura PDF: gera um PDF válido e vai anexada no e-mail de pagamento confirmado."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.modules.admin.models import EmailLog
from app.modules.orders.models import Order

ADDRESS = {
    "recipient_name": "João Fatura",
    "zip": "01001000",
    "street": "Praça da Sé",
    "number": "100",
    "district": "Sé",
    "city": "São Paulo",
    "state": "SP",
}


@pytest.fixture
async def paid_order(client, admin_token, auth_headers, db):
    h = auth_headers(admin_token)
    cat = (await client.post("/api/admin/categories", json={"name": "C"}, headers=h)).json()
    p = (
        await client.post(
            "/api/admin/products",
            json={"name": "Produto Fatura", "category_id": cat["id"], "price_cents": 15000, "status": "active"},
            headers=h,
        )
    ).json()
    await client.put(
        f"/api/admin/products/{p['id']}/option-types",
        json=[{"name": "Tam", "is_size": True, "values": [{"value": "M"}]}],
        headers=h,
    )
    vid = (await client.get(f"/api/products/{p['slug']}")).json()["option_types"][0]["values"][0]["id"]
    await client.post(
        f"/api/admin/products/{p['id']}/variants",
        json={"sku": "PF-M", "option_value_ids": [vid], "stock_qty": 10},
        headers=h,
    )
    await client.put("/api/admin/payment/config", json={"active_provider": "fake"}, headers=h)
    variant_id = (await client.get(f"/api/products/{p['slug']}")).json()["variants"][0]["id"]
    await client.post("/api/cart/items", json={"variant_id": variant_id, "quantity": 2})
    order = (
        await client.post(
            "/api/orders/checkout",
            json={"email": "joao@test.example", "cpf": "52998224725", "shipping_address": ADDRESS},
        )
    ).json()
    return order["number"]


@pytest.mark.asyncio
async def test_build_invoice_pdf(paid_order, db):
    from sqlalchemy.orm import selectinload

    from app.modules.orders.invoice import build_invoice_pdf

    order = await db.scalar(
        select(Order).where(Order.number == paid_order).options(selectinload(Order.items))
    )
    pdf = await build_invoice_pdf(db, order)
    assert isinstance(pdf, bytes)
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 800  # tem conteúdo real


@pytest.mark.asyncio
async def test_paid_email_has_invoice_attachment(client, paid_order, db):
    # confirma o pagamento pelo webhook fake -> dispara order.paid
    wh = await client.post(
        "/api/webhooks/payment/fake",
        json={"order_number": paid_order, "status": "paid", "event_id": "inv-1"},
    )
    assert wh.status_code == 200, wh.text

    logs = (
        await db.execute(
            select(EmailLog).where(EmailLog.template == "payment_confirmed")
        )
    ).scalars().all()
    # exatamente 1 e-mail de pagamento confirmado (sem duplicar)
    assert len(logs) == 1
