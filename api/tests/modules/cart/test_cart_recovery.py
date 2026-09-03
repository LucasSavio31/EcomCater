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
