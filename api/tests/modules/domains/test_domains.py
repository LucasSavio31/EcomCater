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

    async def fake_ensure_site(self, hostname):
        return None

    async def fake_set_proxy(self, *, hostname, upstream):
        calls.append(hostname)

    async def fake_reload(self):
        return None

    monkeypatch.setattr(AaPanelClient, "ensure_site", fake_ensure_site)
    monkeypatch.setattr(AaPanelClient, "set_reverse_proxy", fake_set_proxy)
    monkeypatch.setattr(AaPanelClient, "reload_web_server", fake_reload)

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
    async def fake_ensure_site(self, hostname):
        return None

    async def fake_set_proxy(self, *, hostname, upstream):
        return None

    async def fake_reload(self):
        return None

    async def fake_issue_ssl(self, hostname, *, email=""):
        return None

    async def fake_find_zone(self, hostname):
        # zona já existe e já está ativa -> não passa por "awaiting_nameservers"
        return {"id": "zone-123", "status": "active", "name_servers": ["bob.ns.cloudflare.com"]}

    async def fake_upsert(self, *, zone_id, name, record_type, content, proxied=True):
        return None

    monkeypatch.setattr(AaPanelClient, "ensure_site", fake_ensure_site)
    monkeypatch.setattr(AaPanelClient, "set_reverse_proxy", fake_set_proxy)
    monkeypatch.setattr(AaPanelClient, "reload_web_server", fake_reload)
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

    async def fake_ensure_site(self, hostname):
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

    monkeypatch.setattr(AaPanelClient, "ensure_site", fake_ensure_site)
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

    async def fake_ensure_site(self, hostname):
        return None

    async def fake_set_proxy(self, *, hostname, upstream):
        return None

    async def fake_reload(self):
        return None

    async def fake_issue_ssl(self, hostname, *, email=""):
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

    monkeypatch.setattr(AaPanelClient, "ensure_site", fake_ensure_site)
    monkeypatch.setattr(AaPanelClient, "set_reverse_proxy", fake_set_proxy)
    monkeypatch.setattr(AaPanelClient, "reload_web_server", fake_reload)
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


@pytest.mark.asyncio
async def test_cache_page_options_listed(client, admin_token, auth_headers):
    r = await client.get("/api/admin/domains", headers=auth_headers(admin_token))
    keys = {o["key"] for o in r.json()["cache_page_options"]}
    assert keys == {"home", "categoria", "produto", "pagina", "busca"}


@pytest.mark.asyncio
async def test_cache_pages_requires_confirmed_zone(client, admin_token, auth_headers):
    h = auth_headers(admin_token)
    created = await client.post(
        "/api/admin/domains", json={"hostname": "semzoneainda.com.br"}, headers=h
    )
    domain_id = created.json()["id"]
    r = await client.put(
        f"/api/admin/domains/{domain_id}/cache",
        json={"pages": ["home", "produto"]},
        headers=h,
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_cache_pages_forbidden_for_staff(client, staff_token, auth_headers):
    r = await client.put(
        "/api/admin/domains/00000000-0000-0000-0000-000000000000/cache",
        json={"pages": []},
        headers=auth_headers(staff_token),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_apply_cache_pages_builds_bypass_and_cache_rules(
    client, admin_token, auth_headers, monkeypatch
):
    from app.modules.domains.cloudflare_client import CloudflareClient as CFClient

    captured: dict = {}

    async def fake_find_zone(self, hostname):
        return {"id": "zone-abc", "status": "active", "name_servers": ["a.ns.cloudflare.com"]}

    async def fake_upsert(self, *, zone_id, name, record_type, content, proxied=True):
        return None

    async def fake_set_cache_rules(self, *, zone_id, rules):
        captured["zone_id"] = zone_id
        captured["rules"] = rules

    monkeypatch.setattr(CFClient, "find_zone", fake_find_zone)
    monkeypatch.setattr(CFClient, "upsert_dns_record", fake_upsert)
    monkeypatch.setattr(CFClient, "set_cache_rules", fake_set_cache_rules)

    h = auth_headers(admin_token)
    await client.put(
        "/api/admin/domains/credentials",
        json={"cloudflare_api_token": "fake-token", "server_ip": "167.86.92.107"},
        headers=h,
    )
    created = await client.post(
        "/api/admin/domains", json={"hostname": "cacheteste.com.br"}, headers=h
    )
    domain_id = created.json()["id"]
    assert created.json()["dns_managed_by_cloudflare"] is True  # zona já ativa

    r = await client.put(
        f"/api/admin/domains/{domain_id}/cache",
        json={"pages": ["home", "produto"]},
        headers=h,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["cache_pages"] == ["home", "produto"]
    assert data["cache_applied_at"] is not None

    assert captured["zone_id"] == "zone-abc"
    rules = captured["rules"]
    # no máximo 7 regras (2 bypass + até 5 de cache) -- teto de 10 do plano Free
    assert len(rules) <= 7
    descriptions = [rule["description"] for rule in rules]
    bypass_rule = next(r for r in rules if "carrinho" in r["expression"])
    # bypass consolidado numa regra só (com "or"), não uma por caminho
    for path in ("/carrinho", "/checkout", "/minha-conta", "/favoritos", "/esqueci-senha", "/redefinir-senha"):
        assert path in bypass_rule["expression"]
    sub_rule = next(r for r in rules if "admin.cacheteste.com.br" in r["expression"])
    assert "api.cacheteste.com.br" in sub_rule["expression"]
    # só as páginas selecionadas viram regra de cache
    assert "cache: home" in descriptions
    assert "cache: produto" in descriptions


# ------------------------------------------------ troca de domínio (arquivo-gatilho)

def _mock_full_provision(monkeypatch):
    """Mocka aaPanel + Cloudflare pra provisão terminar em `active` de
    verdade (sem Cloudflare, o fluxo pára em `dns_pending` -- não dispara
    o gatilho de troca)."""
    async def fake_ensure_site(self, hostname):
        return None

    async def fake_set_proxy(self, *, hostname, upstream):
        return None

    async def fake_reload(self):
        return None

    async def fake_issue_ssl(self, hostname, *, email=""):
        return None

    async def fake_find_zone(self, hostname):
        return {"id": "zone-123", "status": "active", "name_servers": ["bob.ns.cloudflare.com"]}

    async def fake_upsert(self, *, zone_id, name, record_type, content, proxied=True):
        return None

    monkeypatch.setattr(AaPanelClient, "ensure_site", fake_ensure_site)
    monkeypatch.setattr(AaPanelClient, "set_reverse_proxy", fake_set_proxy)
    monkeypatch.setattr(AaPanelClient, "reload_web_server", fake_reload)
    monkeypatch.setattr(AaPanelClient, "issue_ssl", fake_issue_ssl)
    monkeypatch.setattr(CloudflareClient, "find_zone", fake_find_zone)
    monkeypatch.setattr(CloudflareClient, "upsert_dns_record", fake_upsert)


_FULL_CREDENTIALS = {
    "aapanel_url": "http://127.0.0.1:7800",
    "aapanel_api_key": "fake-key",
    "cloudflare_api_token": "fake-token",
    "server_ip": "167.86.92.107",
}


@pytest.mark.asyncio
async def test_first_domain_going_active_writes_switch_trigger(
    client, admin_token, auth_headers, monkeypatch, tmp_path
):
    """1º domínio cadastrado (por isso já nasce `is_primary`) ficando ativo
    pede a troca sozinho -- sem precisar de "tornar principal" manual."""
    import json

    from app.core.config import settings

    monkeypatch.setattr(settings, "deploy_trigger_dir", str(tmp_path))
    _mock_full_provision(monkeypatch)

    h = auth_headers(admin_token)
    await client.put("/api/admin/domains/credentials", json=_FULL_CREDENTIALS, headers=h)
    r = await client.post(
        "/api/admin/domains", json={"hostname": "primeirodominio.com.br"}, headers=h
    )
    data = r.json()
    assert data["status"] == "active"
    assert data["is_primary"] is True
    assert data["switch_requested_at"] is not None

    trigger = json.loads((tmp_path / "domain-switch.json").read_text())
    assert trigger["mode"] == "domain"
    assert trigger["hostname"] == "primeirodominio.com.br"
    assert trigger["admin_hostname"] == "admin.primeirodominio.com.br"
    assert trigger["api_hostname"] == "api.primeirodominio.com.br"

    # retry não escreve de novo (switch_requested_at já setado)
    (tmp_path / "domain-switch.json").unlink()
    await client.post(f"/api/admin/domains/{data['id']}/retry", headers=h)
    assert not (tmp_path / "domain-switch.json").exists()


@pytest.mark.asyncio
async def test_set_primary_requires_active_domain(client, admin_token, auth_headers, monkeypatch):
    h = auth_headers(admin_token)
    await client.put(
        "/api/admin/domains/credentials",
        json={"aapanel_url": "http://127.0.0.1:7800", "aapanel_api_key": "fake-key"},
        headers=h,
    )
    created = await client.post(
        "/api/admin/domains", json={"hostname": "semaapanel.com.br"}, headers=h
    )
    assert created.json()["status"] == "failed"  # sem mock, aaPanel real inacessível

    r = await client.post(
        f"/api/admin/domains/{created.json()['id']}/set-primary", headers=h
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_set_primary_switches_and_writes_trigger(
    client, admin_token, auth_headers, monkeypatch, tmp_path
):
    import json

    from app.core.config import settings

    monkeypatch.setattr(settings, "deploy_trigger_dir", str(tmp_path))
    _mock_full_provision(monkeypatch)

    h = auth_headers(admin_token)
    await client.put("/api/admin/domains/credentials", json=_FULL_CREDENTIALS, headers=h)
    first = (
        await client.post("/api/admin/domains", json={"hostname": "um.com.br"}, headers=h)
    ).json()
    second = (
        await client.post("/api/admin/domains", json={"hostname": "dois.com.br"}, headers=h)
    ).json()
    assert first["is_primary"] is True
    assert second["is_primary"] is False

    (tmp_path / "domain-switch.json").unlink()  # limpa o gatilho do 1º (bootstrap)

    r = await client.post(f"/api/admin/domains/{second['id']}/set-primary", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["is_primary"] is True

    trigger = json.loads((tmp_path / "domain-switch.json").read_text())
    assert trigger["hostname"] == "dois.com.br"

    listed = (await client.get("/api/admin/domains", headers=h)).json()["domains"]
    by_host = {d["hostname"]: d for d in listed}
    assert by_host["um.com.br"]["is_primary"] is False
    assert by_host["dois.com.br"]["is_primary"] is True


@pytest.mark.asyncio
async def test_removing_primary_domain_requests_ip_mode(
    client, admin_token, auth_headers, monkeypatch, tmp_path
):
    """Remover o domínio principal tem que voltar o acesso pra IP:PORTA --
    senão o lojista fica sem conseguir entrar na loja/admin."""
    import json

    from app.core.config import settings

    monkeypatch.setattr(settings, "deploy_trigger_dir", str(tmp_path))
    _mock_full_provision(monkeypatch)

    h = auth_headers(admin_token)
    await client.put("/api/admin/domains/credentials", json=_FULL_CREDENTIALS, headers=h)
    created = (
        await client.post("/api/admin/domains", json={"hostname": "vaisair.com.br"}, headers=h)
    ).json()
    (tmp_path / "domain-switch.json").unlink()  # limpa o gatilho do bootstrap

    r = await client.delete(f"/api/admin/domains/{created['id']}", headers=h)
    assert r.status_code == 200, r.text

    trigger = json.loads((tmp_path / "domain-switch.json").read_text())
    assert trigger["mode"] == "ip"


@pytest.mark.asyncio
async def test_removing_non_primary_domain_does_not_touch_trigger(
    client, admin_token, auth_headers, monkeypatch, tmp_path
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "deploy_trigger_dir", str(tmp_path))
    _mock_full_provision(monkeypatch)

    h = auth_headers(admin_token)
    await client.put("/api/admin/domains/credentials", json=_FULL_CREDENTIALS, headers=h)
    await client.post("/api/admin/domains", json={"hostname": "primario.com.br"}, headers=h)
    second = (
        await client.post("/api/admin/domains", json={"hostname": "secundario.com.br"}, headers=h)
    ).json()
    (tmp_path / "domain-switch.json").unlink()  # limpa o gatilho do bootstrap (1º domínio)

    r = await client.delete(f"/api/admin/domains/{second['id']}", headers=h)
    assert r.status_code == 200, r.text
    assert not (tmp_path / "domain-switch.json").exists()
