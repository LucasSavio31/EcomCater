"""Smoke da Fase 1: health, tema, discovery de módulos e auth de admin/cliente."""
from __future__ import annotations

import pytest

from app.core.config import settings
from app.core.security import hash_password
from app.modules.admin.models import AdminUser


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_theme_public(client):
    r = await client.get("/api/theme")
    assert r.status_code == 200
    assert "primary_color" in r.json()


@pytest.mark.asyncio
async def test_modules_registered(client, db):
    # cria um admin e loga para acessar /api/admin/modules
    db.add(
        AdminUser(
            email="root@test.local",
            name="Root",
            password_hash=hash_password("supersecret1"),
            role="super_admin",
            must_change_password=False,
        )
    )
    await db.commit()

    login = await client.post(
        "/api/admin/auth/login",
        json={"email": "root@test.local", "password": "supersecret1"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    mods = await client.get(
        "/api/admin/modules", headers={"Authorization": f"Bearer {token}"}
    )
    assert mods.status_code == 200
    slugs = {m["slug"] for m in mods.json()}
    assert {"products", "categories", "orders", "payment", "shipping", "admin"} <= slugs


@pytest.mark.asyncio
async def test_customer_register_and_me(client):
    reg = await client.post(
        "/api/customers/auth/register",
        json={
            "full_name": "Fulano de Tal",
            "email": "fulano@test.local",
            "password": "clientsecret1",
        },
    )
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]

    me = await client.get(
        "/api/customers/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "fulano@test.local"


@pytest.mark.asyncio
async def test_customer_scope_cannot_hit_admin(client):
    reg = await client.post(
        "/api/customers/auth/register",
        json={"full_name": "Beltrano", "email": "beltrano@test.local", "password": "clientsecret1"},
    )
    token = reg.json()["access_token"]
    r = await client.get(
        "/api/admin/modules", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code in (401, 403)
