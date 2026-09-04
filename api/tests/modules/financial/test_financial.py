"""Livro-caixa financeiro (menu Faturamento).

Garante que faturamento/estorno/cancelamento/total de pedidos:
- são gravados a partir dos eventos de pedido;
- calculam líquido = bruto - custo e margem;
- CONTINUAM valendo mesmo depois que o pedido é excluído.
"""
from __future__ import annotations

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


@pytest.fixture
async def variant_with_cost(client, admin_token, auth_headers):
    """Produto ativo com preço 70,00 e custo 30,00, uma variação em estoque."""
    h = auth_headers(admin_token)
    cat = (await client.post("/api/admin/categories", json={"name": "F"}, headers=h)).json()
    p = (
        await client.post(
            "/api/admin/products",
            json={
                "name": "Item Custo",
                "category_id": cat["id"],
                "price_cents": 7000,
                "cost_cents": 3000,
                "status": "active",
            },
            headers=h,
        )
    ).json()
    detail = (await client.get(f"/api/admin/products/{p['id']}", headers=h)).json()
    assert detail["cost_cents"] == 3000
    await client.put(
        f"/api/admin/products/{p['id']}/option-types",
        json=[{"name": "T", "values": [{"value": "U"}]}],
        headers=h,
    )
    vid = (await client.get(f"/api/products/{p['slug']}")).json()["option_types"][0]["values"][0]["id"]
    v = (
        await client.post(
            f"/api/admin/products/{p['id']}/variants",
            json={"sku": "FC-U", "option_value_ids": [vid], "stock_qty": 10},
            headers=h,
        )
    ).json()
    return v["id"]


async def _order(client, variant, email):
    await client.post("/api/cart/items", json={"variant_id": variant, "quantity": 1})
    r = await client.post(
        "/api/orders/checkout", json={"email": email, "shipping_address": ADDRESS}
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _summary(client, h):
    r = await client.get("/api/admin/financial/summary", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.asyncio
async def test_paid_order_feeds_ledger_with_net_and_margin(client, variant_with_cost, admin_token, auth_headers):
    h = auth_headers(admin_token)
    order = await _order(client, variant_with_cost, "led1@test.example")
    await client.post(
        f"/api/admin/orders/{order['number']}/status", json={"status": "paid"}, headers=h
    )

    s = await _summary(client, h)
    assert s["orders_total"] >= 1
    assert s["gross_cents"] == 7000
    assert s["cost_cents"] == 3000
    assert s["net_cents"] == 4000
    assert s["margin_pct"] == pytest.approx(round(4000 / 7000 * 100, 1))
    assert any(pt["gross_cents"] == 7000 for pt in s["series"])


@pytest.mark.asyncio
async def test_ledger_survives_order_deletion(client, variant_with_cost, admin_token, auth_headers):
    h = auth_headers(admin_token)
    order = await _order(client, variant_with_cost, "led2@test.example")
    await client.post(
        f"/api/admin/orders/{order['number']}/status", json={"status": "paid"}, headers=h
    )
    before = await _summary(client, h)

    # só se apaga pedido já cancelado (dado do pedido some, o livro-caixa não)
    await client.post(
        f"/api/admin/orders/{order['number']}/status", json={"status": "canceled"}, headers=h
    )
    d = await client.delete(
        f"/api/admin/orders/{order['number']}", params={"confirm": "true"}, headers=h
    )
    assert d.status_code == 204, d.text

    after = await _summary(client, h)
    assert after["gross_cents"] == before["gross_cents"]
    assert after["net_cents"] == before["net_cents"]
    assert after["orders_total"] == before["orders_total"]


@pytest.mark.asyncio
async def test_cancellation_is_recorded(client, variant_with_cost, admin_token, auth_headers):
    h = auth_headers(admin_token)
    order = await _order(client, variant_with_cost, "led3@test.example")
    await client.post(
        f"/api/admin/orders/{order['number']}/status", json={"status": "canceled"}, headers=h
    )
    s = await _summary(client, h)
    assert s["canceled_count"] >= 1


@pytest.mark.asyncio
async def test_backfill_seeds_ledger_for_existing_orders(client, variant_with_cost, admin_token, auth_headers):
    from app.scripts.backfill_financial_ledger import run

    h = auth_headers(admin_token)
    order = await _order(client, variant_with_cost, "back1@test.example")
    await client.post(
        f"/api/admin/orders/{order['number']}/status", json={"status": "paid"}, headers=h
    )

    # apaga só os eventos para simular pedidos anteriores à feature
    from sqlalchemy import text as _text

    from app.core.database import SessionLocal

    async with SessionLocal() as db:
        await db.execute(_text("DELETE FROM financial_events"))
        await db.execute(_text("UPDATE order_items SET unit_cost_cents = NULL"))
        await db.commit()

    zeroed = await _summary(client, h)
    assert zeroed["gross_cents"] == 0

    out = await run()
    assert out["orders_scanned"] >= 1

    healed = await _summary(client, h)
    assert healed["gross_cents"] == 7000
    assert healed["cost_cents"] == 13000  # custo padrão do backfill
    assert healed["orders_total"] >= 1

    # rodar de novo não duplica
    await run()
    again = await _summary(client, h)
    assert again["gross_cents"] == healed["gross_cents"]
    assert again["orders_total"] == healed["orders_total"]


@pytest.mark.asyncio
async def test_dashboard_uses_ledger_numbers(client, variant_with_cost, admin_token, auth_headers):
    """A dash tem que refletir o mesmo faturamento do menu Faturamento."""
    h = auth_headers(admin_token)
    order = await _order(client, variant_with_cost, "led4@test.example")
    await client.post(
        f"/api/admin/orders/{order['number']}/status", json={"status": "paid"}, headers=h
    )
    s = await _summary(client, h)
    dash = (await client.get("/api/admin/dashboard", headers=h)).json()
    assert dash["revenue_period_cents"] == s["gross_cents"]
    assert dash["orders_period"] == s["orders_total"]
