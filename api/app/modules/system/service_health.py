"""Verificação de saúde da infraestrutura — roda ao vivo a cada chamada e
guarda um histórico curto por serviço (para as barrinhas tipo Uptime Kuma)."""
from __future__ import annotations

import os
import shutil
import time
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.system.models import HealthSample

# quantas amostras mostrar em cada barra
HISTORY_LEN = 40
# Cada barra = uma janela fixa de 15 min, ancorada em horário redondo
# (…:00, :15, :30, :45). Grava no máximo 1 amostra por serviço por janela; o
# `checked_at` é sempre o início da janela, então todas as barras ficam alinhadas.
# O histórico é PERMANENTE — nunca é podado.
BUCKET_SECONDS = 15 * 60


def _bucket_start(dt: datetime) -> datetime:
    """Início da janela de 15 min que contém `dt` (…:00, :15, :30, :45)."""
    epoch = dt.timestamp()
    return datetime.fromtimestamp(epoch - (epoch % BUCKET_SECONDS), tz=dt.tzinfo or UTC)


def _mib(n: int) -> float:
    return round(n / (1024 * 1024), 1)


async def _check_database(db: AsyncSession) -> tuple[str, int, str]:
    t0 = time.perf_counter()
    await db.execute(text("SELECT 1"))
    ms = int((time.perf_counter() - t0) * 1000)
    status = "ok" if ms < 250 else "degraded"
    return status, ms, f"consulta em {ms} ms"


async def _check_migrations(db: AsyncSession) -> tuple[str, int, str]:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    try:
        current = await db.scalar(text("SELECT version_num FROM alembic_version"))
    except Exception:  # noqa: BLE001
        await db.rollback()  # a query falha aborta a transação — limpa antes de seguir
        return "down", 0, "tabela alembic_version ausente"
    try:
        cfg = Config(os.path.join(os.getcwd(), "alembic.ini"))
        head = ScriptDirectory.from_config(cfg).get_current_head()
    except Exception:  # noqa: BLE001
        head = None
    if head and current and head != current:
        return "degraded", 0, f"banco em {current}, código em {head}"
    return "ok", 0, f"em dia ({current})"


def _check_cache() -> tuple[str, int, str]:
    url = settings.redis_url or ""
    if url.startswith("fakeredis"):
        return "ok", 0, "fakeredis (em memória)"
    try:
        import redis  # type: ignore

        t0 = time.perf_counter()
        client = redis.from_url(url, socket_connect_timeout=1)
        client.ping()
        ms = int((time.perf_counter() - t0) * 1000)
        return ("ok" if ms < 200 else "degraded"), ms, f"PING em {ms} ms"
    except Exception as exc:  # noqa: BLE001
        return "down", 0, f"sem resposta: {exc}"


def _check_storage() -> tuple[str, int, str]:
    path = settings.storage_local_dir
    probe = os.path.join(path, ".healthcheck")
    last_exc: Exception | None = None
    # O ponto de montagem do volume pode "sumir" por um instante durante a
    # recriação do container. Isso não é falha de storage — tenta de novo
    # algumas vezes antes de pintar vermelho.
    for attempt in range(4):
        try:
            os.makedirs(path, exist_ok=True)
            with open(probe, "w") as fh:
                fh.write("ok")
            os.remove(probe)
            usage = shutil.disk_usage(path)
            free_pct = usage.free / usage.total * 100
            status = "ok" if free_pct > 10 else "degraded"
            return status, 0, f"{_mib(usage.free)} MiB livres ({free_pct:.0f}%)"
        except OSError as exc:
            last_exc = exc
            if attempt < 3:
                time.sleep(0.3)
        except Exception as exc:  # noqa: BLE001
            return "down", 0, f"não gravável: {exc}"
    return "down", 0, f"não gravável após 4 tentativas: {last_exc}"


async def _check_backup(db: AsyncSession) -> tuple[str, int, str]:
    """Saúde do backup agendado: último resultado + se está atrasado."""
    from app.modules.system.models import BackupSettings

    row = await db.get(BackupSettings, 1)
    if not row or not row.auto_enabled:
        return "degraded", 0, "backup automático desligado"
    if row.last_status == "error":
        return "down", 0, "último backup falhou — ver Sistema → Backup"
    if not row.last_run_at:
        return "degraded", 0, "nenhum backup executado ainda"
    last = row.last_run_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    age_h = (datetime.now(UTC) - last).total_seconds() / 3600
    limit = {"semanal": 24 * 8, "mensal": 24 * 32}.get(row.frequency, 26)  # diário: 26h
    if age_h > limit:
        return "degraded", 0, f"último backup há {age_h:.0f}h (esperado a cada {limit}h)"
    return "ok", 0, f"último há {age_h:.0f}h ({row.frequency})"


async def _check_smtp(db: AsyncSession) -> tuple[str, int, str]:
    from app.modules.admin.models import SmtpSettings

    row = await db.get(SmtpSettings, 1)
    host = (row.host if row else None) or settings.smtp_host
    if not host or host in ("mailpit", "localhost"):
        return "degraded", 0, "usando fallback local (configure em E-mail/SMTP)"
    return "ok", 0, f"host {host}"


async def _check_melhor_envio(db: AsyncSession) -> tuple[str, int, str]:
    """Disponibilidade da API do Melhor Envio + validade do token."""
    from app.modules.shipping.service import _me_base, load_config

    cfg = await load_config(db)
    token = cfg.melhor_envio_token or settings.melhor_envio_token
    if not token:
        return "degraded", 0, "sem token configurado (menu Frete)"
    base = _me_base(cfg)
    amb = "sandbox" if "sandbox" in base else "produção"
    try:
        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(
                f"{base}/api/v2/me",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "User-Agent": settings.melhor_envio_user_agent,
                },
            )
        ms = int((time.perf_counter() - t0) * 1000)
    except Exception as exc:  # noqa: BLE001
        return "down", 0, f"sem resposta: {exc}"
    if r.status_code in (401, 403):
        return "down", ms, f"token inválido ou expirado ({amb})"
    if r.status_code >= 500:
        return "down", ms, f"instável: HTTP {r.status_code} ({amb})"
    if r.status_code >= 300:
        return "degraded", ms, f"HTTP {r.status_code} ({amb})"
    return ("ok" if ms < 1500 else "degraded"), ms, f"conectado ({amb}) em {ms} ms"


async def _check_appmax(db: AsyncSession) -> tuple[str, int, str]:
    """Disponibilidade da API da Appmax (gateway de pagamento) + token."""
    from app.modules.payment.service import load_config as load_payment_config

    cfg = await load_payment_config(db)
    if cfg.active_provider != "appmax":
        return "degraded", 0, f"gateway ativo: {cfg.active_provider} (Appmax desligada)"
    token = cfg.appmax_access_token or settings.appmax_access_token
    base = settings.appmax_api_url
    if not cfg.appmax_sandbox:
        base = base.replace("homolog.sandboxappmax.com.br", "admin.appmax.com.br")
    amb = "sandbox" if cfg.appmax_sandbox else "produção"
    if not token:
        return "degraded", 0, "sem token configurado (menu Pagamento)"
    try:
        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=8) as c:
            # chamada leve: sem dados de cliente a Appmax responde erro de
            # validação — o que já prova que a API está no ar e o token foi aceito.
            r = await c.post(f"{base}/customer", json={"access-token": token})
        ms = int((time.perf_counter() - t0) * 1000)
    except Exception as exc:  # noqa: BLE001
        return "down", 0, f"sem resposta: {exc}"
    body: dict = {}
    try:
        body = r.json() if r.content else {}
    except ValueError:
        body = {}
    txt = str(body.get("text") or body.get("message") or "").lower()
    bad_token = r.status_code in (401, 403) or (
        "token" in txt and any(w in txt for w in ("inv", "unauth", "autoriz", "denied"))
    )
    if bad_token:
        return "down", ms, f"token inválido ({amb})"
    if r.status_code >= 500:
        return "down", ms, f"instável: HTTP {r.status_code} ({amb})"
    return ("ok" if ms < 2000 else "degraded"), ms, f"conectado ({amb}) em {ms} ms"


def _slug(name: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")[:28]


def _check_containers() -> list[tuple[str, str, tuple[str, int, str]]]:
    """Saúde dos containers Docker, se o servidor tiver acesso ao Docker.
    Sem Docker (ex.: dev nativo desta máquina) devolve lista vazia."""
    import json as _json
    import subprocess

    docker = shutil.which("docker")
    if not docker:
        return []
    try:
        res = subprocess.run(
            [docker, "ps", "-a", "--no-trunc", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=6,
        )
    except Exception:  # noqa: BLE001
        return []
    if res.returncode != 0:
        return []

    out: list[tuple[str, str, tuple[str, int, str]]] = []
    for line in res.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            c = _json.loads(line)
        except ValueError:
            continue
        name = c.get("Names") or c.get("Name") or c.get("ID", "?")
        state = (c.get("State") or "").lower()
        status_txt = c.get("Status") or ""
        low = status_txt.lower()
        if "unhealthy" in low or state in ("dead",):
            st = "down"
        elif state == "running" and "health: starting" not in low and "restarting" not in low:
            st = "ok" if "unhealthy" not in low else "down"
        elif state in ("restarting", "paused", "created") or "starting" in low:
            st = "degraded"
        elif state in ("exited",):
            st = "down"
        else:
            st = "degraded"
        out.append((f"container:{_slug(name)}", f"Container · {name}", (st, 0, status_txt or state)))
    return out


async def _alert_health_transition(
    db: AsyncSession, key: str, label: str, status: str, detail: str
) -> None:
    """Manda e-mail ao admin quando um serviço entra em problema ou normaliza."""
    try:
        from app.shared import mailer

        await mailer.send(
            db,
            to=await mailer.admin_notify_email(db),
            template="health_alert",
            context={
                "bad": status != "ok",
                "service_label": label,
                "status_pt": mailer.STATUS_PT.get(status, status),
                "detail": detail,
                "when": datetime.now(UTC).strftime("%d/%m/%Y %H:%M UTC"),
            },
        )
    except Exception:  # noqa: BLE001
        import logging

        logging.getLogger("system.health").warning(
            "falha ao enviar alerta de saúde de %s", key, exc_info=True
        )


async def run_checks(db: AsyncSession, *, persist: bool = True) -> list[dict]:
    now = datetime.now(UTC)
    checks: list[tuple[str, str, tuple[str, int, str]]] = []

    checks.append(("api", "API", ("ok", 0, "respondendo")))
    checks.append(("database", "Banco de dados", await _check_database(db)))
    checks.append(("migrations", "Migrations", await _check_migrations(db)))
    checks.append(("cache", "Cache / Redis", _check_cache()))
    checks.append(("storage", "Armazenamento de mídia", _check_storage()))
    checks.append(("smtp", "E-mail (SMTP)", await _check_smtp(db)))
    checks.append(("backup", "Backup agendado", await _check_backup(db)))
    checks.append(("melhor_envio", "API Melhor Envio", await _check_melhor_envio(db)))
    checks.append(("appmax", "API Appmax (pagamento)", await _check_appmax(db)))
    checks.extend(_check_containers())

    # Escalonamento: 2 leituras "instável" (laranja) seguidas + esta ainda
    # instável e sem voltar ao normal => "fora do ar" (vermelho). Uma vez
    # vermelho, só um check "ok" tira desse estado.
    recent = await db.execute(
        select(HealthSample.service_key, HealthSample.status)
        .where(HealthSample.checked_at >= now - timedelta(days=2))
        .order_by(HealthSample.checked_at.desc())
    )
    last2: dict[str, list[str]] = {}
    for k, st in recent.all():
        lst = last2.setdefault(k, [])
        if len(lst) < 2:
            lst.append(st)
    checks = [
        (
            key,
            label,
            (
                ("down", ms, f"instável há 3 verificações seguidas — {detail}")
                if status == "degraded"
                and len(last2.get(key, [])) >= 2
                and all(s != "ok" for s in last2[key])
                else (status, ms, detail)
            ),
        )
        for key, label, (status, ms, detail) in checks
    ]

    if persist:
        # 1 amostra por serviço por janela de 15 min; timestamp = início da janela
        bucket = _bucket_start(now)
        last_rows = await db.execute(
            select(HealthSample.service_key, func.max(HealthSample.checked_at)).group_by(
                HealthSample.service_key
            )
        )
        last_at = dict(last_rows.all())
        for key, _label, (status, ms, detail) in checks:
            prev = last_at.get(key)
            if prev is not None:
                # normaliza `prev` para aware (colunas antigas podem vir naïve)
                if prev.tzinfo is None:
                    prev = prev.replace(tzinfo=UTC)
                if _bucket_start(prev) >= bucket:
                    continue  # já há amostra nesta janela
            db.add(
                HealthSample(
                    service_key=key,
                    status=status,
                    latency_ms=ms,
                    detail=detail[:300],
                    checked_at=bucket,
                )
            )
            # alerta por e-mail na TRANSIÇÃO (ok -> problema, ou problema -> ok).
            # `last2[key][0]` é o status persistido mais recente.
            prev_status = (last2.get(key) or [None])[0]
            if prev_status and prev_status != status and (prev_status == "ok" or status == "ok"):
                await _alert_health_transition(db, key, next(
                    (lb for k, lb, _ in checks if k == key), key), status, detail)
        await db.commit()  # histórico é permanente — nunca podamos

    # histórico recente para as barrinhas
    history: dict[str, list[dict]] = {}
    rows = await db.scalars(
        select(HealthSample)
        .where(HealthSample.checked_at >= now - timedelta(days=7))
        .order_by(HealthSample.checked_at.desc())
    )
    for s in rows:
        bucket = history.setdefault(s.service_key, [])
        if len(bucket) < HISTORY_LEN:
            bucket.append(
                {
                    "status": s.status,
                    "latency_ms": s.latency_ms,
                    "at": s.checked_at.isoformat(),
                }
            )

    out: list[dict] = []
    for key, label, (status, ms, detail) in checks:
        hist = list(reversed(history.get(key, [])))
        total = len(hist) or 1
        up = sum(1 for h in hist if h["status"] == "ok")
        out.append(
            {
                "key": key,
                "label": label,
                "status": status,
                "latency_ms": ms,
                "detail": detail,
                "uptime_pct": round(up / total * 100, 1),
                "history": hist,
                "checked_at": now.isoformat(),
            }
        )
    return out


_LABELS = {
    "api": "API",
    "database": "Banco de dados",
    "migrations": "Migrations",
    "cache": "Cache / Redis",
    "storage": "Armazenamento de mídia",
    "smtp": "E-mail (SMTP)",
    "melhor_envio": "API Melhor Envio",
    "appmax": "API Appmax (pagamento)",
}


async def history(
    db: AsyncSession, *, since: datetime, until: datetime, service_key: str | None = None
) -> list[dict]:
    """Histórico PERMANENTE agregado por serviço no intervalo [since, until]."""
    stmt = (
        select(HealthSample)
        .where(HealthSample.checked_at >= since, HealthSample.checked_at <= until)
        .order_by(HealthSample.checked_at.asc())
    )
    if service_key:
        stmt = stmt.where(HealthSample.service_key == service_key)

    by_key: dict[str, list[dict]] = {}
    for s in await db.scalars(stmt):
        by_key.setdefault(s.service_key, []).append(
            {"status": s.status, "latency_ms": s.latency_ms, "detail": s.detail,
             "at": s.checked_at.isoformat()}
        )

    out: list[dict] = []
    for key, samples in sorted(by_key.items()):
        total = len(samples)
        up = sum(1 for x in samples if x["status"] == "ok")
        down = sum(1 for x in samples if x["status"] == "down")
        lats = [x["latency_ms"] for x in samples if x["latency_ms"]]
        out.append(
            {
                "key": key,
                "label": _LABELS.get(key, key.replace("container:", "Container · ")),
                "samples": samples,
                "count": total,
                "uptime_pct": round(up / total * 100, 1) if total else 0,
                "incidents": down,
                "avg_latency_ms": round(sum(lats) / len(lats)) if lats else 0,
                "first_at": samples[0]["at"] if samples else None,
                "last_at": samples[-1]["at"] if samples else None,
            }
        )
    return out
