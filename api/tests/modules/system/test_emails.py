"""E-mails transacionais de pedido: confirmação (cliente), aviso (lojista) e
dados de acesso da conta criada no checkout. Roda com API_ENV=test — o
`mailer.send` não abre SMTP, mas renderiza os templates e grava em `email_log`.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.modules.admin.models import EmailLog

VALID_CPF = "52998224725"  # CPF de teste clássico (válido nos dígitos verificadores)

ADDRESS = {
    "recipient_name": "Cliente Novo",
    "zip": "01001000",
    "street": "Praça da Sé",
    "number": "100",
    "district": "Sé",
    "city": "São Paulo",
    "state": "SP",
}


@pytest.fixture
async def product(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    cat = (await client.post("/api/admin/categories", json={"name": "Geral"}, headers=h)).json()
    p = (
        await client.post(
            "/api/admin/products",
            json={"name": "Item E-mail", "category_id": cat["id"], "price_cents": 12345, "status": "active"},
            headers=h,
        )
    ).json()
    await client.put(
        f"/api/admin/products/{p['id']}/option-types",
        json=[{"name": "Tam", "is_size": True, "values": [{"value": "U"}]}],
        headers=h,
    )
    vid = (await client.get(f"/api/products/{p['slug']}")).json()["option_types"][0]["values"][0]["id"]
    v = (
        await client.post(
            f"/api/admin/products/{p['id']}/variants",
            json={"sku": "EM-U", "option_value_ids": [vid], "stock_qty": 5},
            headers=h,
        )
    ).json()
    await client.put("/api/admin/payment/config", json={"active_provider": "fake"}, headers=h)
    return {"variant_id": v["id"], "slug": p["slug"]}


@pytest.mark.asyncio
async def test_guest_checkout_sends_three_emails(client, product, db):
    await client.post("/api/cart/items", json={"variant_id": product["variant_id"], "quantity": 2})
    r = await client.post(
        "/api/orders/checkout",
        json={"email": "guest@test.example", "cpf": VALID_CPF, "shipping_address": ADDRESS},
    )
    assert r.status_code == 201, r.text
    number = r.json()["number"]

    logs = (await db.execute(select(EmailLog).order_by(EmailLog.created_at))).scalars().all()
    by_tpl = {log.template: log for log in logs}

    # 1) confirmação para o cliente, com o número no assunto
    assert "order_created" in by_tpl
    assert number in by_tpl["order_created"].subject
    assert by_tpl["order_created"].to_email == "guest@test.example"

    # 2) aviso para a conta de administrador (super admin do fixture)
    assert "admin_order_created" in by_tpl
    assert by_tpl["admin_order_created"].to_email == "root@test.example"

    # 3) dados de acesso (login = e-mail + CPF) para o comprador
    assert "account_access" in by_tpl
    assert by_tpl["account_access"].to_email == "guest@test.example"

    # o e-mail de "cadastro explícito" NÃO deve sair no fluxo de checkout
    assert "account_created" not in by_tpl


@pytest.mark.asyncio
async def test_order_email_body_has_payment_and_shipping(db):
    """Renderiza o template do cliente e confere que o corpo traz itens,
    total, pagamento e endereço."""
    from app.shared.mailer import TEMPLATES, _env

    _subj, body_tpl = TEMPLATES["order_created"]
    html = _env.from_string(body_tpl).render(
        number="2026-000999",
        items=[{"name": "Tênis X", "qty": 2, "variant": "42", "line_cents": 20000}],
        items_total_cents=20000,
        discount_cents=1000,
        coupon_code="DEZ",
        shipping_cents=2500,
        total_cents=21500,
        payment_method="Pix",
        installments=1,
        pix_qr="000201...br.gov.bcb.pix",
        boleto_url=None,
        shipping_method="SEDEX",
        shipping_eta=3,
        tracking_code=None,
        address={
            "recipient": "Cliente Novo",
            "line": "Praça da Sé, 100",
            "district": "Sé",
            "city": "São Paulo",
            "state": "SP",
            "zip": "01001000",
        },
    )
    assert "Tênis X" in html
    assert "R$ 215.00" in html  # total
    assert "Pix" in html
    assert "SEDEX" in html
    assert "Praça da Sé, 100" in html
    assert "DEZ" in html  # cupom no desconto
