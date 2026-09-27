"""SMTP por domínio: venda no domínio X manda e-mail pelo SMTP de X; sem
SMTP próprio, pelo principal."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.modules.admin.models import EmailLog
from app.modules.domains import sites
from app.modules.domains.models import STATUS_ACTIVE, Domain
from app.shared import mailer

ADDRESS = {
    "recipient_name": "Cliente B",
    "zip": "20040002",
    "street": "Av. Rio Branco",
    "number": "1",
    "district": "Centro",
    "city": "Rio de Janeiro",
    "state": "RJ",
}


@pytest.fixture
async def domains(db):
    db.add_all([
        Domain(hostname="loja-a.com.br", is_primary=True, status=STATUS_ACTIVE),
        Domain(hostname="loja-b.com.br", status=STATUS_ACTIVE),
        Domain(hostname="loja-c.com.br", status=STATUS_ACTIVE),
    ])
    await db.commit()
    sites.invalidate()
    yield
    sites.invalidate()


@pytest.mark.asyncio
async def test_admin_links_smtp_to_domain(client, admin_token, auth_headers, domains, db):
    h = auth_headers(admin_token)
    await client.put("/api/admin/smtp", json={"host": "smtp.principal.com", "from_email": "loja@a.com"}, headers=h)
    r = await client.put(
        "/api/admin/smtp/domains/loja-b.com.br",
        json={"host": "smtp.b.com", "port": 465, "use_ssl": True, "from_email": "vendas@loja-b.com.br",
              "password": "segredo"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["password_set"] is True and "password" not in r.json()

    listing = {d["hostname"]: d for d in (await client.get("/api/admin/smtp/domains", headers=h)).json()}
    assert listing["loja-a.com.br"]["is_primary"] is True
    assert listing["loja-b.com.br"]["uses_primary"] is False
    assert listing["loja-b.com.br"]["smtp"]["from_email"] == "vendas@loja-b.com.br"
    assert listing["loja-c.com.br"]["uses_primary"] is True

    # escolha do SMTP no envio
    assert (await mailer._smtp_conf(db, "loja-b.com.br"))["host"] == "smtp.b.com"
    assert (await mailer._smtp_conf(db, "loja-c.com.br"))["host"] == "smtp.principal.com"  # reserva
    assert (await mailer._smtp_conf(db, None))["host"] == "smtp.principal.com"

    # desvincular volta pro principal; principal e domínio não cadastrado recusam
    assert (await client.delete("/api/admin/smtp/domains/loja-b.com.br", headers=h)).status_code == 200
    assert (await mailer._smtp_conf(db, "loja-b.com.br"))["host"] == "smtp.principal.com"
    assert (await client.put("/api/admin/smtp/domains/loja-a.com.br", json={}, headers=h)).status_code == 422
    assert (await client.put("/api/admin/smtp/domains/outro.com", json={}, headers=h)).status_code == 404


@pytest.mark.asyncio
async def test_order_emails_leave_through_sale_domain(client, admin_token, auth_headers, domains, db):
    h = auth_headers(admin_token)
    await client.put("/api/admin/smtp/domains/loja-b.com.br", json={"host": "smtp.b.com"}, headers=h)

    cat = (await client.post("/api/admin/categories", json={"name": "C"}, headers=h)).json()
    p = (await client.post(
        "/api/admin/products",
        json={"name": "Item", "category_id": cat["id"], "price_cents": 7000, "status": "active"},
        headers=h,
    )).json()
    v = (await client.post(
        f"/api/admin/products/{p['id']}/variants",
        json={"sku": "SMTP-B", "option_value_ids": [], "stock_qty": 5},
        headers=h,
    )).json()
    await client.post("/api/cart/items", json={"variant_id": v["id"], "quantity": 1})
    r = await client.post(
        "/api/orders/checkout",
        json={"email": "b@test.example", "shipping_address": ADDRESS},
        headers={"Origin": "https://loja-b.com.br"},
    )
    assert r.status_code == 201, r.text
    order = r.json()

    from app.core.events import emit

    await emit("order.created", {"order_id": order["id"], "number": order["number"]})
    log = await db.scalar(
        select(EmailLog).where(EmailLog.order_id == order["id"], EmailLog.template == "order_created")
    )
    assert log is not None and log.site_host == "loja-b.com.br"

    from app.modules.orders.codes import order_store_url

    assert order_store_url(order["number"], "loja-b.com.br").startswith("https://loja-b.com.br/minha-conta")
