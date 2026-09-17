"""Testes do módulo `domains`: gate de super_admin + orquestração de provisionamento."""
from __future__ import annotations

import pytest
import pytest_asyncio

from app.modules.domains.aapanel_client import AaPanelClient
from app.modules.domains.cloudflare_client import CloudflareClient


@pytest_asyncio.fixture
async def staff_token(client, db) -> str:
    """Admin comum (não super_admin) — usado pra provar que os endpoints de
    domínio recusam quem não é super_admin."""
    from app.core.security import hash_password
    from app.modules.admin.models import AdminUser

    db.add(
        AdminUser(
            email="staff@test.example",
            name="Staff",
            password_hash=hash_password("supersecret1"),
            role="admin",
            must_change_password=False,
        )
    )
    await db.commit()
    r = await client.post(
        "/api/admin/auth/login",
        json={"email": "staff@test.example", "password": "supersecret1"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_plain_admin_forbidden(client, staff_token, auth_headers):
    r = await client.get("/api/admin/domains", headers=auth_headers(staff_token))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_allowed(client, admin_token, auth_headers):
    r = await client.get("/api/admin/domains", headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert r.json()["domains"] == []


@pytest.mark.asyncio
async def test_add_domain_without_credentials_marks_failed(client, admin_token, auth_headers):
    r = await client.post(
        "/api/admin/domains",
        json={"hostname": "minhaloja.com.br"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "failed"
    assert "aaPanel" in data["last_error"]
    assert data["admin_hostname"] == "admin.minhaloja.com.br"
    assert data["api_hostname"] == "api.minhaloja.com.br"


@pytest.mark.asyncio
async def test_add_domain_is_idempotent(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    first = await client.post(
        "/api/admin/domains", json={"hostname": "minhaloja.com.br"}, headers=h
    )
    second = await client.post(
        "/api/admin/domains", json={"hostname": "minhaloja.com.br"}, headers=h
    )
    assert first.json()["id"] == second.json()["id"]

    listed = await client.get("/api/admin/domains", headers=h)
    assert len(listed.json()["domains"]) == 1


@pytest.mark.asyncio
async def test_provision_with_aapanel_but_no_dns_ends_dns_pending(
    client, admin_token, auth_headers, monkeypatch
):
    calls: list[str] = []

    async def fake_create_proxy(self, *, hostname, upstream):
        calls.append(hostname)

    monkeypatch.setattr(AaPanelClient, "create_reverse_proxy_site", fake_create_proxy)

    h = auth_headers(admin_token)
    await client.put(
        "/api/admin/domains/credentials",
        json={"aapanel_url": "http://127.0.0.1:7800", "aapanel_api_key": "fake-key"},
        headers=h,
    )
    r = await client.post(
        "/api/admin/domains", json={"hostname": "minhaloja.com.br"}, headers=h
    )
    data = r.json()
    assert data["status"] == "dns_pending"
    assert sorted(calls) == sorted(
        ["minhaloja.com.br", "admin.minhaloja.com.br", "api.minhaloja.com.br"]
    )


@pytest.mark.asyncio
async def test_provision_full_success_with_cloudflare(
    client, admin_token, auth_headers, monkeypatch
):
    async def fake_create_proxy(self, *, hostname, upstream):
        return None

    async def fake_issue_ssl(self, hostname, *, extra_domains=None):
        return None

    async def fake_find_zone(self, hostname):
        # zona já existe e já está ativa -> não passa por "awaiting_nameservers"
        return {"id": "zone-123", "status": "active", "name_servers": ["bob.ns.cloudflare.com"]}

    async def fake_upsert(self, *, zone_id, name, record_type, content, proxied=True):
        return None

    monkeypatch.setattr(AaPanelClient, "create_reverse_proxy_site", fake_create_proxy)
    monkeypatch.setattr(AaPanelClient, "issue_ssl", fake_issue_ssl)
    monkeypatch.setattr(CloudflareClient, "find_zone", fake_find_zone)
    monkeypatch.setattr(CloudflareClient, "upsert_dns_record", fake_upsert)

    h = auth_headers(admin_token)
    await client.put(
        "/api/admin/domains/credentials",
        json={
            "aapanel_url": "http://127.0.0.1:7800",
            "aapanel_api_key": "fake-key",
            "cloudflare_api_token": "fake-token",
            "server_ip": "167.86.92.107",
        },
        headers=h,
    )
    r = await client.post(
        "/api/admin/domains", json={"hostname": "minhaloja.com.br"}, headers=h
    )
    data = r.json()
    assert data["status"] == "active"
    assert data["ssl_status"] == "issued"
    assert data["dns_managed_by_cloudflare"] is True


@pytest.mark.asyncio
async def test_new_cloudflare_domain_awaits_nameservers(
    client, admin_token, auth_headers, monkeypatch
):
    """Zona nova (ainda não existe na Cloudflare): a API cria a zona, devolve
    os nameservers pra gente mostrar na tela, JÁ cria os registros A/CNAME
    (a Cloudflare aceita numa zona "pending", só não ficam públicos ainda) e
    o domínio fica `awaiting_nameservers` até o usuário trocar isso no
    registrador — SEM tentar aaPanel/SSL ainda."""
    aapanel_calls: list[str] = []
    dns_calls: list[tuple[str, str, str]] = []

    async def fake_create_proxy(self, *, hostname, upstream):
        aapanel_calls.append(hostname)

    async def fake_find_zone(self, hostname):
        return None  # zona ainda não existe na conta

    async def fake_create_zone(self, hostname):
        return {
            "id": "zone-novo",
            "status": "pending",
            "name_servers": ["bob.ns.cloudflare.com", "kate.ns.cloudflare.com"],
        }

    async def fake_upsert(self, *, zone_id, name, record_type, content, proxied=True):
        dns_calls.append((name, record_type, content))

    monkeypatch.setattr(AaPanelClient, "create_reverse_proxy_site", fake_create_proxy)
    monkeypatch.setattr(CloudflareClient, "find_zone", fake_find_zone)
    monkeypatch.setattr(CloudflareClient, "create_zone", fake_create_zone)
    monkeypatch.setattr(CloudflareClient, "upsert_dns_record", fake_upsert)

    h = auth_headers(admin_token)
    await client.put(
        "/api/admin/domains/credentials",
        json={
            "aapanel_url": "http://127.0.0.1:7800",
            "aapanel_api_key": "fake-key",
            "cloudflare_api_token": "fake-token",
            "server_ip": "167.86.92.107",
        },
        headers=h,
    )
    r = await client.post(
        "/api/admin/domains", json={"hostname": "novo-dominio.com.br"}, headers=h
    )
    data = r.json()
    assert data["status"] == "awaiting_nameservers"
    assert data["dns_confirmed"] is False
    assert data["cloudflare_nameservers"] == ["bob.ns.cloudflare.com", "kate.ns.cloudflare.com"]
    assert aapanel_calls == []  # não tenta vhost antes de confirmar o DNS
    assert ("novo-dominio.com.br", "A", "167.86.92.107") in dns_calls
    assert ("admin.novo-dominio.com.br", "CNAME", "novo-dominio.com.br") in dns_calls
    assert ("api.novo-dominio.com.br", "CNAME", "novo-dominio.com.br") in dns_calls


@pytest.mark.asyncio
async def test_retry_confirms_once_nameservers_propagate(
    client, admin_token, auth_headers, monkeypatch
):
    """Depois que a zona vira `active` (nameservers propagaram), um retry
    confirma o DNS de vez (`dns_confirmed_at` gravado) e segue pro resto do
    provisionamento — sem checar a zona de novo nas tentativas seguintes."""
    zone_status = {"value": "pending"}
    zone_checks: list[str] = []

    async def fake_create_proxy(self, *, hostname, upstream):
        return None

    async def fake_issue_ssl(self, hostname, *, extra_domains=None):
        return None

    async def fake_find_zone(self, hostname):
        zone_checks.append(hostname)
        return {
            "id": "zone-novo",
            "status": zone_status["value"],
            "name_servers": ["bob.ns.cloudflare.com"],
        }

    async def fake_upsert(self, *, zone_id, name, record_type, content, proxied=True):
        return None

    monkeypatch.setattr(AaPanelClient, "create_reverse_proxy_site", fake_create_proxy)
    monkeypatch.setattr(AaPanelClient, "issue_ssl", fake_issue_ssl)
    monkeypatch.setattr(CloudflareClient, "find_zone", fake_find_zone)
    monkeypatch.setattr(CloudflareClient, "upsert_dns_record", fake_upsert)

    h = auth_headers(admin_token)
    await client.put(
        "/api/admin/domains/credentials",
        json={
            "aapanel_url": "http://127.0.0.1:7800",
            "aapanel_api_key": "fake-key",
            "cloudflare_api_token": "fake-token",
            "server_ip": "167.86.92.107",
        },
        headers=h,
    )
    created = await client.post(
        "/api/admin/domains", json={"hostname": "novo-dominio.com.br"}, headers=h
    )
    assert created.json()["status"] == "awaiting_nameservers"
    assert len(zone_checks) == 1

    zone_status["value"] = "active"  # usuário trocou os nameservers no registrador
    retried = await client.post(
        f"/api/admin/domains/{created.json()['id']}/retry", headers=h
    )
    data = retried.json()
    assert data["status"] == "active"
    assert data["dns_confirmed"] is True
    assert len(zone_checks) == 2

    # confirmado -> uma 2ª tentativa (falha de aaPanel, digamos) não pinga a
    # zona de novo
    zone_status["value"] = "pending"  # se checasse de novo, isso quebraria
    await client.post(f"/api/admin/domains/{created.json()['id']}/retry", headers=h)
    assert len(zone_checks) == 2


@pytest.mark.asyncio
async def test_credentials_test_endpoint(client, admin_token, auth_headers, monkeypatch):
    async def fake_ping(self):
        return None

    async def fake_verify_fail(self):
        from app.modules.domains.cloudflare_client import CloudflareError

        raise CloudflareError("Token da Cloudflare inválido ou inativo.")

    monkeypatch.setattr(AaPanelClient, "ping", fake_ping)
    monkeypatch.setattr(CloudflareClient, "verify_token", fake_verify_fail)

    r = await client.post(
        "/api/admin/domains/credentials/test",
        json={
            "aapanel_url": "http://127.0.0.1:7800",
            "aapanel_api_key": "fake-key",
            "cloudflare_api_token": "bad-token",
        },
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["aapanel_ok"] is True
    assert data["cloudflare_ok"] is False
    assert "inválido" in data["cloudflare_message"]


@pytest.mark.asyncio
async def test_credentials_test_forbidden_for_staff(client, staff_token, auth_headers):
    r = await client.post(
        "/api/admin/domains/credentials/test", json={}, headers=auth_headers(staff_token)
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_delete_domain(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    created = await client.post(
        "/api/admin/domains", json={"hostname": "outro.com.br"}, headers=h
    )
    domain_id = created.json()["id"]
    r = await client.delete(f"/api/admin/domains/{domain_id}", headers=h)
    assert r.status_code == 200

    listed = await client.get("/api/admin/domains", headers=h)
    assert listed.json()["domains"] == []
