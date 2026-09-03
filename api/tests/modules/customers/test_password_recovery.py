"""Recuperação de acesso: esqueci a senha (cliente e admin) e esqueci o e-mail."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.modules.admin.models import EmailLog, PasswordReset

VALID_CPF = "52998224725"


async def _make_customer(client, email="dono@test.example", cpf=VALID_CPF, pw="senha-antiga"):
    r = await client.post(
        "/api/customers/auth/register",
        json={"full_name": "Dono", "email": email, "password": pw, "cpf": cpf},
    )
    assert r.status_code == 201, r.text
    return email


@pytest.mark.asyncio
async def test_customer_forgot_and_reset(client, db):
    await _make_customer(client)

    # pede o link (por e-mail)
    r = await client.post("/api/customers/auth/forgot-password", json={"email": "dono@test.example"})
    assert r.status_code == 202

    row = (await db.execute(select(PasswordReset))).scalars().first()
    assert row is not None and row.subject_type == "customer" and row.used_at is None

    log = (
        await db.execute(select(EmailLog).where(EmailLog.template == "password_reset"))
    ).scalars().first()
    assert log is not None and log.to_email == "dono@test.example"

    # gera um token conhecido e redefine
    from app.shared.pwreset import create_reset

    raw = await create_reset(db, "customer", row.subject_id)
    await db.commit()

    r = await client.post(
        "/api/customers/auth/reset-password", json={"token": raw, "new_password": "senha-nova-123"}
    )
    assert r.status_code == 204, r.text

    # login com a senha nova funciona; a antiga não
    ok = await client.post(
        "/api/customers/auth/login", json={"email": "dono@test.example", "password": "senha-nova-123"}
    )
    assert ok.status_code == 200
    bad = await client.post(
        "/api/customers/auth/login", json={"email": "dono@test.example", "password": "senha-antiga"}
    )
    assert bad.status_code == 401

    # token de uso único: segunda vez falha
    again = await client.post(
        "/api/customers/auth/reset-password", json={"token": raw, "new_password": "outra-123"}
    )
    assert again.status_code == 422


@pytest.mark.asyncio
async def test_forgot_unknown_email_is_silent(client):
    r = await client.post("/api/customers/auth/forgot-password", json={"email": "ninguem@x.test"})
    assert r.status_code == 202  # mesma resposta, sem vazar existência


@pytest.mark.asyncio
async def test_recover_email_by_cpf(client):
    await _make_customer(client, email="lucas.savio@gmail.com", cpf=VALID_CPF)
    r = await client.post("/api/customers/auth/recover-email", json={"cpf": "529.982.247-25"})
    assert r.status_code == 200
    body = r.json()
    assert body["found"] is True
    assert body["email_masked"].endswith("@gmail.com")
    assert body["email_masked"] != "lucas.savio@gmail.com"
    assert "*" in body["email_masked"]

    miss = await client.post("/api/customers/auth/recover-email", json={"cpf": "11144477735"})
    assert miss.json()["found"] is False


@pytest.mark.asyncio
async def test_admin_forgot_and_reset(client, db, admin_token):
    # admin_token cria root@test.example (super admin)
    r = await client.post("/api/admin/auth/forgot-password", json={"email": "root@test.example"})
    assert r.status_code == 202

    row = (
        await db.execute(select(PasswordReset).where(PasswordReset.subject_type == "admin"))
    ).scalars().first()
    assert row is not None

    from app.shared.pwreset import create_reset

    raw = await create_reset(db, "admin", row.subject_id)
    await db.commit()

    short = await client.post(
        "/api/admin/auth/reset-password", json={"token": raw, "new_password": "curta"}
    )
    assert short.status_code == 422  # painel exige >= 8

    r = await client.post(
        "/api/admin/auth/reset-password", json={"token": raw, "new_password": "PainelNovo1"}
    )
    assert r.status_code == 204

    ok = await client.post(
        "/api/admin/auth/login", json={"email": "root@test.example", "password": "PainelNovo1"}
    )
    assert ok.status_code == 200
