"""Testes do módulo `analytics`: config pública (loja) e admin, com foco no
campo novo do Google Merchant Center (verificação de propriedade do site)."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_public_config_defaults_disabled(client):
    r = await client.get("/api/analytics/config")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["merchant_center_enabled"] is False
    assert data["merchant_center_verification_code"] is None


@pytest.mark.asyncio
async def test_admin_get_requires_admin(client):
    r = await client.get("/api/admin/analytics")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_can_save_merchant_center_verification_code(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    r = await client.put(
        "/api/admin/analytics",
        json={
            "merchant_center_enabled": True,
            "merchant_center_verification_code": "uu3TmG9kfL5y4JIc2ixj7PE4VDl87lvTtjaHX4a8Qn8",
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["merchant_center_enabled"] is True
    assert body["merchant_center_verification_code"] == "uu3TmG9kfL5y4JIc2ixj7PE4VDl87lvTtjaHX4a8Qn8"

    # aparece na config pública -- é o que a loja usa pra montar a meta tag
    pub = (await client.get("/api/analytics/config")).json()
    assert pub["merchant_center_enabled"] is True
    assert pub["merchant_center_verification_code"] == "uu3TmG9kfL5y4JIc2ixj7PE4VDl87lvTtjaHX4a8Qn8"


@pytest.mark.asyncio
async def test_merchant_center_enabled_requires_code(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    r = await client.put(
        "/api/admin/analytics",
        json={"merchant_center_enabled": True, "merchant_center_verification_code": None},
        headers=h,
    )
    assert r.status_code in (400, 422), r.text


@pytest.mark.asyncio
async def test_merchant_center_code_trimmed(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    r = await client.put(
        "/api/admin/analytics",
        json={"merchant_center_enabled": True, "merchant_center_verification_code": "  abc123  "},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["merchant_center_verification_code"] == "abc123"
