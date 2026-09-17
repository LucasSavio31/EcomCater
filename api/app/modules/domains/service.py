"""Config do módulo (aaPanel/Cloudflare) + orquestração de provisionamento."""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationError
from app.modules.domains.aapanel_client import AaPanelClient, AaPanelError
from app.modules.domains.cloudflare_client import CloudflareClient, CloudflareError
from app.modules.domains.config import DomainsConfig
from app.modules.domains.models import (
    STATUS_ACTIVE,
    STATUS_AWAITING_NAMESERVERS,
    STATUS_DNS_PENDING,
    STATUS_FAILED,
    STATUS_PROVISIONING,
    Domain,
)

logger = logging.getLogger("domains.service")


def _uuid(v: str) -> uuid.UUID:
    try:
        return uuid.UUID(v)
    except ValueError as exc:
        raise ValidationError("id inválido") from exc

# portas internas do `cater-proxy` (nginx no Docker), só acessíveis em
# 127.0.0.1 na VPS depois que o aaPanel assume as portas 80/443 públicas.
_UPSTREAM_STORE = "http://127.0.0.1:3000"
_UPSTREAM_ADMIN = "http://127.0.0.1:3001"
_UPSTREAM_API = "http://127.0.0.1:8000"


def admin_hostname(hostname: str) -> str:
    return f"admin.{hostname}"


def api_hostname(hostname: str) -> str:
    return f"api.{hostname}"


# --------------------------------------------------------------- config
async def load_config(db: AsyncSession) -> DomainsConfig:
    from app.modules.admin.models import ModuleRow

    row = await db.get(ModuleRow, "domains")
    raw = dict(row.config_json) if row and row.config_json else {}
    return DomainsConfig(**raw)


async def test_connection(db: AsyncSession, draft: dict) -> dict:
    """Testa aaPanel + Cloudflare com os valores do formulário (ainda não
    salvos) por cima da config já salva — assim dá pra testar antes de
    clicar em Salvar, ou testar o que já está gravado (campo vazio no
    formulário = mantém o valor salvo). Nunca persiste nada."""
    saved = await load_config(db)
    merged = saved.model_copy(update={k: v for k, v in draft.items() if v})

    aapanel_ok = False
    aapanel_message = "Preencha URL e API key do aaPanel."
    if merged.aapanel_url and merged.aapanel_api_key:
        try:
            await AaPanelClient(base_url=merged.aapanel_url, api_key=merged.aapanel_api_key).ping()
            aapanel_ok = True
            aapanel_message = "Conectado."
        except AaPanelError as exc:
            aapanel_message = str(exc)

    cloudflare_ok = False
    cloudflare_message = "Preencha o token da Cloudflare (opcional — sem ele, o DNS fica manual)."
    if merged.cloudflare_api_token:
        try:
            await CloudflareClient(api_token=merged.cloudflare_api_token).verify_token()
            cloudflare_ok = True
            cloudflare_message = "Token válido."
        except CloudflareError as exc:
            cloudflare_message = str(exc)

    return {
        "aapanel_ok": aapanel_ok,
        "aapanel_message": aapanel_message,
        "cloudflare_ok": cloudflare_ok,
        "cloudflare_message": cloudflare_message,
    }


async def save_config(db: AsyncSession, patch: dict) -> DomainsConfig:
    from app.modules.admin.models import ModuleRow

    row = await db.get(ModuleRow, "domains")
    current = dict(row.config_json) if row and row.config_json else {}
    for k, v in patch.items():
        if v is not None:
            current[k] = v
    cfg = DomainsConfig(**current)
    if row is None:
        row = ModuleRow(slug="domains", enabled=True, config_json=cfg.model_dump())
        db.add(row)
    else:
        row.config_json = cfg.model_dump()
    row.updated_at = datetime.now(UTC)
    await db.flush()
    return cfg


# --------------------------------------------------------------- domínios
async def list_domains(db: AsyncSession) -> list[Domain]:
    result = await db.scalars(select(Domain).order_by(Domain.created_at))
    return list(result)


async def get_domain(db: AsyncSession, domain_id: str) -> Domain | None:
    return await db.get(Domain, _uuid(domain_id))


async def upsert_domain(db: AsyncSession, hostname: str) -> Domain:
    hostname = hostname.strip().lower()
    existing = await db.scalar(select(Domain).where(Domain.hostname == hostname))
    if existing:
        return existing
    is_first = (await db.scalar(select(Domain.id).limit(1))) is None
    domain = Domain(hostname=hostname, is_primary=is_first)
    db.add(domain)
    await db.flush()
    return domain


async def delete_domain(db: AsyncSession, domain: Domain) -> None:
    await db.delete(domain)


# --------------------------------------------------------------- provisionamento
async def provision(db: AsyncSession, domain: Domain) -> None:
    """Roda os passos de DNS (opcional) + vhost + SSL. Grava status/erro no domínio.

    Síncrono e best-effort: erro num passo não impede os seguintes fazerem
    sentido tentar de novo depois (`scheduler.py` reprocessa
    `awaiting_nameservers`/`dns_pending`/`failed`), então cada etapa é isolada
    em seu próprio try/except.
    """
    cfg = await load_config(db)
    domain.last_error = None

    # Fase 1 (só Cloudflare, só até confirmar uma vez): garante que a zona
    # existe e checa se os nameservers já foram trocados no registrador. Uma
    # vez confirmado (`dns_confirmed_at` gravado), NUNCA mais checa de novo
    # pra este domínio — só se ele for removido e recadastrado.
    confirmed = bool(domain.dns_confirmed_at)
    if cfg.cloudflare_api_token and not domain.dns_confirmed_at:
        confirmed = await _sync_cloudflare_zone(cfg, domain)
        if confirmed:
            domain.dns_confirmed_at = datetime.now(UTC)

    # Os registros A/CNAME são criados assim que a zona existe — a Cloudflare
    # aceita registros numa zona ainda "pending" (não-ativa), eles só não
    # ficam públicos até os nameservers propagarem. Não precisa esperar a
    # confirmação pra isso, só a existência da zona.
    if cfg.cloudflare_api_token and cfg.server_ip and domain.cloudflare_zone_id:
        await _apply_cloudflare_records(cfg, domain)

    if cfg.cloudflare_api_token and not confirmed:
        domain.status = STATUS_AWAITING_NAMESERVERS
        domain.last_checked_at = datetime.now(UTC)
        await db.flush()
        return

    domain.status = STATUS_PROVISIONING
    await db.flush()

    dns_ok = domain.dns_managed_by_cloudflare

    if not cfg.aapanel_url or not cfg.aapanel_api_key:
        domain.status = STATUS_FAILED
        domain.last_error = "aaPanel não configurado — cadastre a URL e a API key em Credenciais."
        domain.last_checked_at = datetime.now(UTC)
        await db.flush()
        return

    client = AaPanelClient(base_url=cfg.aapanel_url, api_key=cfg.aapanel_api_key)
    try:
        await client.create_reverse_proxy_site(hostname=domain.hostname, upstream=_UPSTREAM_STORE)
        await client.create_reverse_proxy_site(
            hostname=admin_hostname(domain.hostname), upstream=_UPSTREAM_ADMIN
        )
        await client.create_reverse_proxy_site(
            hostname=api_hostname(domain.hostname), upstream=_UPSTREAM_API
        )
    except AaPanelError as exc:
        logger.warning("aaPanel: falha ao criar vhost de %s: %s", domain.hostname, exc)
        domain.status = STATUS_FAILED
        domain.last_error = f"Proxy reverso: {exc}"
        domain.last_checked_at = datetime.now(UTC)
        await db.flush()
        return

    if not dns_ok:
        # vhost criado, mas sem DNS apontando ainda não dá pra emitir SSL
        # (Let's Encrypt precisa resolver o host) — fica pendente pro
        # scheduler tentar de novo depois que o usuário criar o registro.
        domain.status = STATUS_DNS_PENDING
        domain.last_checked_at = datetime.now(UTC)
        await db.flush()
        return

    try:
        await client.issue_ssl(domain.hostname)
        await client.issue_ssl(admin_hostname(domain.hostname))
        await client.issue_ssl(api_hostname(domain.hostname))
    except AaPanelError as exc:
        logger.warning("aaPanel: falha ao emitir SSL de %s: %s", domain.hostname, exc)
        domain.status = STATUS_DNS_PENDING  # tenta de novo no próximo tick (DNS pode ainda não ter propagado)
        domain.ssl_status = "error"
        domain.last_error = f"SSL: {exc}"
        domain.last_checked_at = datetime.now(UTC)
        await db.flush()
        return

    domain.status = STATUS_ACTIVE
    domain.ssl_status = "issued"
    domain.last_error = None
    domain.last_checked_at = datetime.now(UTC)
    await db.flush()


async def _sync_cloudflare_zone(cfg: DomainsConfig, domain: Domain) -> bool:
    """Encontra (ou cria) a zona do domínio na conta Cloudflare, grava os
    nameservers que ela atribuiu (pra mostrar na tela) e informa se a zona já
    está `active` — ou seja, se o registrador já foi atualizado e propagou.
    A criação do registrador em si é sempre manual, em outro provedor."""
    client = CloudflareClient(api_token=cfg.cloudflare_api_token)
    try:
        zone = await client.find_zone(domain.hostname)
        if zone is None:
            zone = await client.create_zone(domain.hostname)
    except CloudflareError as exc:
        logger.warning("Cloudflare: falha ao preparar zona de %s: %s", domain.hostname, exc)
        domain.last_error = f"Cloudflare: {exc}"
        return False

    domain.cloudflare_zone_id = zone["id"]
    domain.cloudflare_nameservers = zone["name_servers"]
    return zone["status"] == "active"


async def _apply_cloudflare_records(cfg: DomainsConfig, domain: Domain) -> None:
    """Cria/atualiza os registros A/CNAME dentro da zona já confirmada. Falha
    aqui não derruba o provisionamento inteiro — os registros manuais
    continuam valendo como plano B, e o próximo tick tenta de novo."""
    client = CloudflareClient(api_token=cfg.cloudflare_api_token)
    try:
        await client.upsert_dns_record(
            zone_id=domain.cloudflare_zone_id,
            name=domain.hostname,
            record_type="A",
            content=cfg.server_ip,
        )
        await client.upsert_dns_record(
            zone_id=domain.cloudflare_zone_id,
            name=admin_hostname(domain.hostname),
            record_type="CNAME",
            content=domain.hostname,
        )
        await client.upsert_dns_record(
            zone_id=domain.cloudflare_zone_id,
            name=api_hostname(domain.hostname),
            record_type="CNAME",
            content=domain.hostname,
        )
    except CloudflareError as exc:
        logger.warning("Cloudflare: falha ao criar registros de %s: %s", domain.hostname, exc)
        domain.dns_managed_by_cloudflare = False
        return

    domain.dns_managed_by_cloudflare = True
