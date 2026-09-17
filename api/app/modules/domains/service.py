"""Config do módulo (aaPanel/Cloudflare) + orquestração de provisionamento."""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationError
from app.modules.domains.aapanel_client import AaPanelClient, AaPanelError
from app.modules.domains.cache_rules import CACHE_PAGE_DEFS, build_rules
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

# cada app (api/frontend/admin) publica direto em 127.0.0.1 -- o aaPanel/
# LiteSpeed é quem fica público nas portas 80/443 e faz o proxy pra cá.
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
    """Remove o domínio. Se era o principal, pede a reversão pra acesso
    direto por IP:PORTA (`_request_domain_switch(None)`) -- sem isso, o
    lojista ficaria sem conseguir acessar loja/admin/API nenhuma: o proxy
    reverso (aaPanel/LiteSpeed) só responde pro hostname configurado, e as
    portas dos containers ficam fechadas pro mundo enquanto há domínio
    ativo (só em 127.0.0.1)."""
    was_primary = domain.is_primary
    await db.delete(domain)
    if was_primary:
        _request_domain_switch(None)


async def set_primary(db: AsyncSession, domain: Domain) -> Domain:
    """Torna este o domínio principal (só 1 por vez) e pede a troca das
    variáveis do site (`.env`) + rebuild do front/admin -- ver
    `_request_domain_switch`. Só permitido com o domínio já ativo (senão
    não tem SSL/DNS prontos pro site funcionar nele)."""
    if domain.status != STATUS_ACTIVE:
        raise ValidationError("O domínio precisa estar ativo (DNS + SSL prontos) antes de virar o principal.")
    others = await db.scalars(select(Domain).where(Domain.id != domain.id, Domain.is_primary.is_(True)))
    for o in others:
        o.is_primary = False
    domain.is_primary = True
    _request_domain_switch(domain)
    await db.flush()
    return domain


def _request_domain_switch(domain: Domain | None) -> None:
    """Escreve o arquivo-gatilho numa pasta compartilhada com o HOST (bind
    mount) -- a API nunca toca em `.env`/Docker diretamente. Um script já
    rodando no servidor (fora do container) lê esse arquivo a cada poucos
    minutos e aplica sozinho: troca as variáveis do site + rebuilda
    front/admin/api. `domain=None` pede o MODO IP -- sem domínio nenhum
    ativo, volta o acesso a ser direto por IP:PORTA (sem TLS), pra nunca
    ficar sem conseguir entrar na loja/admin. Best-effort: se a pasta não
    existir (dev local, bind mount não configurado), só loga e segue -- não
    quebra o fluxo de provisionamento/remoção."""
    import json
    from pathlib import Path

    from app.core.config import settings

    try:
        d = Path(settings.deploy_trigger_dir)
        d.mkdir(parents=True, exist_ok=True)
        if domain is None:
            payload = {"mode": "ip", "requested_at": datetime.now(UTC).isoformat()}
        else:
            payload = {
                "mode": "domain",
                "hostname": domain.hostname,
                "admin_hostname": admin_hostname(domain.hostname),
                "api_hostname": api_hostname(domain.hostname),
                "requested_at": datetime.now(UTC).isoformat(),
            }
            domain.switch_requested_at = datetime.now(UTC)
        (d / "domain-switch.json").write_text(json.dumps(payload, indent=2))
    except OSError:
        logger.warning(
            "não foi possível escrever o arquivo-gatilho de troca de domínio (%s)",
            domain.hostname if domain else "modo IP", exc_info=True,
        )


# --------------------------------------------------------------- provisionamento
async def provision(db: AsyncSession, domain: Domain) -> None:
    """Roda os passos de DNS (opcional) + vhost + SSL. Grava status/erro no domínio.

    Idempotente em toda etapa — pode ser chamado de novo a qualquer momento
    (o `scheduler.py` reprocessa `awaiting_nameservers`/`dns_pending`/
    `failed`, e também `active` com `ssl_status=error`) sem duplicar nada:
    site/proxy reverso são recriados/sobrescritos sem erro se já existirem,
    e falha de SSL não derruba o domínio pra `failed` — o site já funciona
    por HTTP nesse ponto.
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
    hosts = [
        (domain.hostname, _UPSTREAM_STORE),
        (admin_hostname(domain.hostname), _UPSTREAM_ADMIN),
        (api_hostname(domain.hostname), _UPSTREAM_API),
    ]
    try:
        for host, upstream in hosts:
            await client.ensure_site(host)
            await client.set_reverse_proxy(hostname=host, upstream=upstream)
        # um restart só, depois dos 3 — cada `set_reverse_proxy` já escreveu
        # o arquivo; recarregar 3x seguidas não muda nada a mais.
        await client.reload_web_server()
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

    # SSL é best-effort e NÃO derruba o domínio pra `failed`: o site já
    # funciona por HTTP nesse ponto (proxy + DNS ok). Uma falha aqui (ex.:
    # DNS ainda propagando na prática, mesmo com a zona Cloudflare "active")
    # fica registrada em `ssl_status`/`last_error`, e o scheduler tenta nas
    # próximas passagens — sem tirar o site do ar nem marcar erro geral.
    ssl_error: str | None = None
    for host, _upstream in hosts:
        try:
            await client.issue_ssl(host)
        except AaPanelError as exc:
            logger.warning("aaPanel: falha ao emitir SSL de %s: %s", host, exc)
            ssl_error = str(exc)

    domain.status = STATUS_ACTIVE
    domain.last_checked_at = datetime.now(UTC)
    if ssl_error:
        domain.ssl_status = "error"
        domain.last_error = f"SSL: {ssl_error}"
    else:
        domain.ssl_status = "issued"
        domain.last_error = None
    # 1ª vez que ESTE domínio principal fica ativo (o "torna principal"
    # explícito, pra um domínio que já não era o 1º cadastrado, passa por
    # `set_primary`, não por aqui) -- pede a troca das variáveis do site
    # sozinho, uma vez só (`switch_requested_at` evita repetir a cada
    # passagem do scheduler).
    if domain.is_primary and not domain.switch_requested_at:
        _request_domain_switch(domain)
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


# --------------------------------------------------------------- cache (Cloudflare)
async def apply_cache_pages(db: AsyncSession, domain: Domain, pages: list[str]) -> None:
    """Salva quais tipos de página cachear agressivamente e aplica o ruleset
    de Cache Rules na zona Cloudflare do domínio. Carrinho/checkout/conta/
    favoritos/recuperação de senha (e os hosts admin./api.) sempre ficam em
    bypass — não é uma opção, `build_rules` já garante isso.
    """
    valid = [p for p in pages if p in CACHE_PAGE_DEFS]
    if not domain.cloudflare_zone_id:
        raise ValidationError(
            "Este domínio ainda não tem zona Cloudflare confirmada — configure o DNS primeiro."
        )
    cfg = await load_config(db)
    if not cfg.cloudflare_api_token:
        raise ValidationError("Cloudflare não configurada — cadastre o token em Credenciais.")

    client = CloudflareClient(api_token=cfg.cloudflare_api_token)
    rules = build_rules(domain.hostname, valid)
    try:
        await client.set_cache_rules(zone_id=domain.cloudflare_zone_id, rules=rules)
    except CloudflareError as exc:
        raise ValidationError(f"Cloudflare: {exc}") from exc

    domain.cache_pages = valid
    domain.cache_applied_at = datetime.now(UTC)
    await db.flush()
