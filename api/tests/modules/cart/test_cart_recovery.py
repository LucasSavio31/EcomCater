"""Recuperação de carrinho abandonado: CRUD das mensagens (inclui excluir) e
o envio automático (`_process_due`)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.modules.admin.models import EmailLog
from app.modules.cart_recovery.models import AbandonedCart


@pytest.mark.asyncio
async def test_recovery_message_crud_including_delete(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    created = await client.post(
        "/api/admin/cart-recovery/messages",
        json={"position": 1, "delay_minutes": 30, "subject": "Volte!", "body": "Oi {nome}"},
        headers=h,
    )
    assert created.status_code == 201, created.text
    mid = created.json()["id"]

    lst = (await client.get("/api/admin/cart-recovery/messages", headers=h)).json()
    assert any(m["id"] == mid for m in lst)

    dele = await client.request(
        "DELETE", f"/api/admin/cart-recovery/messages/{mid}", headers=h
    )
    assert dele.status_code == 204, dele.text

    lst2 = (await client.get("/api/admin/cart-recovery/messages", headers=h)).json()
    assert all(m["id"] != mid for m in lst2)


@pytest.mark.asyncio
async def test_process_due_sends_once_per_step(client, admin_token, auth_headers, db):
    h = auth_headers(admin_token)
    await client.post(
        "/api/admin/cart-recovery/messages",
        json={"position": 1, "delay_minutes": 0, "subject": "1o aviso", "body": "{link}"},
        headers=h,
    )
    await client.post(
        "/api/admin/cart-recovery/messages",
        json={"position": 2, "delay_minutes": 0, "subject": "2o aviso", "body": "{link}"},
        headers=h,
    )

    db.add(
        AbandonedCart(
            email="abandonou@test.example",
            cart_token="tok-abc",
            total_cents=12900,
            items_count=1,
            created_at=datetime.now(UTC) - timedelta(minutes=5),
        )
    )
    await db.commit()

    from app.modules.cart_recovery.module import _process_due

    r1 = await _process_due(db)
    assert r1["sent"] == 1
    r2 = await _process_due(db)  # ainda não passou o delay do 2º? delay=0 -> manda o 2º
    assert r2["sent"] == 1
    r3 = await _process_due(db)  # acabaram as mensagens -> nada
    assert r3["sent"] == 0

    logs = (
        await db.execute(select(EmailLog).where(EmailLog.template == "cart_recovery"))
    ).scalars().all()
    assert len(logs) == 2
    assert all(log.to_email == "abandonou@test.example" for log in logs)

    ac = await db.scalar(select(AbandonedCart).where(AbandonedCart.email == "abandonou@test.example"))
    assert ac.reminders_sent == 2


@pytest.mark.asyncio
async def test_send_to_carts_forces_send_ignoring_delay(client, admin_token, auth_headers, db):
    h = auth_headers(admin_token)
    await client.post(
        "/api/admin/cart-recovery/messages",
        json={"position": 1, "delay_minutes": 999, "subject": "aviso", "body": "{link}"},
        headers=h,
    )
    db.add(
        AbandonedCart(
            email="forcar@test.example",
            cart_token="tok-force",
            total_cents=5000,
            items_count=1,
            created_at=datetime.now(UTC),  # delay de 999 min -> NÃO estaria vencido
            reminders_sent=1,               # já "esgotou" a única mensagem
        )
    )
    await db.commit()

    r = await client.post(
        "/api/admin/cart-recovery/carts/send",
        json={"ids": [
            str((await db.scalar(select(AbandonedCart).where(AbandonedCart.email == "forcar@test.example"))).id)
        ]},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["sent"] == 1  # reenvia a última mesmo com reminders_sent no limite

    logs = (
        await db.execute(select(EmailLog).where(EmailLog.template == "cart_recovery"))
    ).scalars().all()
    assert any(log.to_email == "forcar@test.example" for log in logs)


@pytest.mark.asyncio
async def test_run_now_force_sends_to_all_pending_ignoring_delay(
    client, admin_token, auth_headers, db
):
    h = auth_headers(admin_token)
    await client.post(
        "/api/admin/cart-recovery/messages",
        json={"position": 1, "delay_minutes": 999, "subject": "aviso", "body": "{link}"},
        headers=h,
    )
    for i in range(3):
        db.add(
            AbandonedCart(
                email=f"pend{i}@test.example",
                cart_token=f"tok-{i}",
                total_cents=1000,
                items_count=1,
                created_at=datetime.now(UTC),  # prazo de 999 min -> nada vencido
                reminders_sent=0,
            )
        )
    await db.commit()

    normal = await client.post("/api/admin/cart-recovery/run-now", headers=h)
    assert normal.json()["sent"] == 0  # sem force respeita o delay

    forced = await client.post("/api/admin/cart-recovery/run-now?force=1", headers=h)
    assert forced.status_code == 200, forced.text
    assert forced.json()["sent"] == 3

    again = await client.post("/api/admin/cart-recovery/run-now?force=1", headers=h)
    assert again.json()["sent"] == 0  # já esgotaram a única mensagem

    logs = (
        await db.execute(select(EmailLog).where(EmailLog.template == "cart_recovery"))
    ).scalars().all()
    assert len(logs) == 3


def test_fill_placeholders():
    from app.modules.cart_recovery.module import _fill

    assert _fill("{nome}, você esqueceu {link}", name="João", link="U") == "João, você esqueceu U"
    # sem nome: some o "{nome}, "
    assert _fill("{nome}, você esqueceu", name="", link="U") == "você esqueceu"
    assert _fill("Olá {nome}, notamos", name="", link="U") == "Olá notamos"


def test_cart_recovery_template_shows_items_and_total():
    from app.shared.mailer import TEMPLATES, _env

    html = _env.from_string(TEMPLATES["cart_recovery"][1]).render(
        subject="Volte",
        body="Olá, você deixou itens",
        cta_url="https://loja/x",
        btn_style="background:#111",
        items=[
            {"name": "Tênis Volt", "variant": "42 / Preto", "qty": 2, "line_cents": 25980},
        ],
        total_cents=25980,
    )
    assert "Tênis Volt" in html
    assert "42 / Preto" in html
    assert "R$ 259.80" in html
    assert "Total" in html
    assert "background:#111" in html  # botão inline
