"""Monitoramento: check de backup, alerta de anomalia e resumo diário."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.modules.admin.models import EmailLog
from app.modules.system.models import BackupSettings


def _local(y, m, d, h, minute=0):
    from zoneinfo import ZoneInfo

    return datetime(y, m, d, h, minute, tzinfo=ZoneInfo("America/Sao_Paulo"))


def test_is_due_first_run_only_at_target_hour():
    from app.modules.system.service_backup import is_due
    from app.modules.system.models import BackupSettings

    cfg = BackupSettings(auto_enabled=True, hour=3, frequency="diario", last_run_at=None)
    assert is_due(cfg, now=_local(2026, 9, 4, 3, 5)) is True
    assert is_due(cfg, now=_local(2026, 9, 4, 15, 0)) is False


def test_is_due_manual_run_at_odd_hour_does_not_push_schedule_a_day(db):
    """Bug real: um backup manual às 15h fazia o agendador esperar 20h
    corridas a partir DAÍ — como isso nunca cai dentro da janela (hora 3), o
    automático perdia o dia inteiro. Agora é por DATA local: rodou hoje (a
    qualquer hora) -> já não roda de novo hoje, mas amanhã na janela roda."""
    from app.modules.system.service_backup import is_due
    from app.modules.system.models import BackupSettings

    cfg = BackupSettings(
        auto_enabled=True, hour=3, frequency="diario",
        last_run_at=_local(2026, 9, 3, 15, 24).astimezone(UTC),
    )
    # mesmo dia do backup manual, na janela normal: já rodou hoje -> não repete
    assert is_due(cfg, now=_local(2026, 9, 3, 3, 5)) is False
    # dia seguinte, na janela: roda normalmente (não ficou "atrasado" a mais)
    assert is_due(cfg, now=_local(2026, 9, 4, 3, 5)) is True
    # dia seguinte, fora da janela: ainda não
    assert is_due(cfg, now=_local(2026, 9, 4, 15, 0)) is False


def test_is_due_catches_up_when_window_is_missed():
    """Se o processo ficou fora do ar durante a janela (ex.: redeploy), o
    agendador não fica esperando o dia seguinte de novo — roda no próximo
    tick, fora da hora, assim que ficar bem atrasado."""
    from app.modules.system.service_backup import is_due
    from app.modules.system.models import BackupSettings

    cfg = BackupSettings(
        auto_enabled=True, hour=3, frequency="diario",
        last_run_at=_local(2026, 9, 2, 3, 5).astimezone(UTC),
    )
    # só 1 dia atrasado, fora da janela: ainda espera
    assert is_due(cfg, now=_local(2026, 9, 3, 20, 0)) is False
    # 2 dias corridos sem rodar: roda AGORA, mesmo fora da hora 3
    assert is_due(cfg, now=_local(2026, 9, 4, 20, 0)) is True


def test_is_due_weekly_monthly_thresholds():
    from app.modules.system.service_backup import is_due
    from app.modules.system.models import BackupSettings

    weekly = BackupSettings(
        auto_enabled=True, hour=3, frequency="semanal",
        last_run_at=_local(2026, 9, 1, 3, 5).astimezone(UTC),
    )
    assert is_due(weekly, now=_local(2026, 9, 4, 3, 5)) is False  # só 3 dias
    assert is_due(weekly, now=_local(2026, 9, 7, 3, 5)) is True  # 6 dias

    monthly = BackupSettings(
        auto_enabled=True, hour=3, frequency="mensal",
        last_run_at=_local(2026, 8, 1, 3, 5).astimezone(UTC),
    )
    assert is_due(monthly, now=_local(2026, 8, 15, 3, 5)) is False  # 14 dias
    assert is_due(monthly, now=_local(2026, 8, 28, 3, 5)) is True  # 27 dias


@pytest.mark.asyncio
async def test_check_backup_states(db):
    from app.modules.system.service_health import _check_backup

    # sem linha -> automático desligado
    status, _ms, _d = await _check_backup(db)
    assert status == "degraded"

    db.add(BackupSettings(id=1, auto_enabled=True, frequency="diario", last_status="error"))
    await db.commit()
    status, _ms, _d = await _check_backup(db)
    assert status == "down"

    row = await db.get(BackupSettings, 1)
    row.last_status = "ok"
    row.last_run_at = datetime.now(UTC) - timedelta(hours=2)
    await db.commit()
    status, _ms, _d = await _check_backup(db)
    assert status == "ok"

    row = await db.get(BackupSettings, 1)
    row.last_run_at = datetime.now(UTC) - timedelta(hours=48)
    await db.commit()
    status, _ms, _d = await _check_backup(db)
    assert status == "degraded"  # atrasado


@pytest.mark.asyncio
async def test_daily_digest_email(db, admin_token):
    """admin_token cria o super admin -> destino do resumo."""
    from app.modules.system.digest import send_daily_digest

    await send_daily_digest(db, label="01/01/2026")

    log = (
        await db.execute(
            select(EmailLog).where(EmailLog.template == "daily_digest").order_by(EmailLog.created_at.desc())
        )
    ).scalars().first()
    assert log is not None
    assert log.to_email == "root@test.example"
    assert "01/01/2026" in log.subject


@pytest.mark.asyncio
async def test_health_alert_fires_on_degraded_to_down_transition(db, admin_token):
    """Antes só alertava se um dos lados fosse "ok" — uma piora de "instável"
    pra "fora do ar" ficava muda. `admin_token` cria o super admin -> destino
    do alerta."""
    from app.modules.system.models import HealthSample
    from app.modules.system.service_health import _bucket_start, run_checks

    prev_bucket = _bucket_start(datetime.now(UTC) - timedelta(minutes=20))
    db.add(
        HealthSample(
            service_key="backup", status="degraded", latency_ms=0,
            detail="nenhum backup executado ainda", checked_at=prev_bucket,
        )
    )
    # backup automático FALHOU de verdade agora -> vira "down"
    db.add(BackupSettings(id=1, auto_enabled=True, frequency="diario", last_status="error"))
    await db.commit()

    await run_checks(db, persist=True)

    log = (
        await db.execute(
            select(EmailLog)
            .where(EmailLog.template == "health_alert")
            .order_by(EmailLog.created_at.desc())
        )
    ).scalars().first()
    assert log is not None
    assert log.to_email == "root@test.example"


@pytest.mark.asyncio
async def test_health_alert_silent_on_ok_to_degraded_transition(db, admin_token):
    """Serviço só ficou lento/instável (nunca chegou a "fora do ar") não deve
    gerar e-mail — antes disparava em QUALQUER mudança de estado, inclusive
    esse ruído de "instável" pontual. `admin_token` cria o super admin."""
    from app.modules.system.models import HealthSample
    from app.modules.system.service_health import _bucket_start, run_checks

    prev_bucket = _bucket_start(datetime.now(UTC) - timedelta(minutes=20))
    db.add(
        HealthSample(
            service_key="backup", status="ok", latency_ms=0,
            detail="último há 1h (diario)", checked_at=prev_bucket,
        )
    )
    # backup automático desligado agora -> vira "degraded" (nunca "down")
    db.add(BackupSettings(id=1, auto_enabled=False, frequency="diario"))
    await db.commit()

    await run_checks(db, persist=True)

    log = (
        await db.execute(
            select(EmailLog).where(EmailLog.template == "health_alert")
        )
    ).scalars().first()
    assert log is None


@pytest.mark.asyncio
async def test_run_checks_isolates_one_failing_check(db, monkeypatch):
    """Uma exceção inesperada em UM check não pode derrubar a amostragem (nem
    o alerta) dos outros — antes, uma falha aqui cancelava `run_checks`
    inteiro no meio, sem persistir nem alertar nada daquele ciclo."""
    from app.modules.system import service_health

    async def _boom(_db):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(service_health, "_check_backup", _boom)

    results = await service_health.run_checks(db, persist=False)
    by_key = {r["key"]: r for r in results}

    assert by_key["backup"]["status"] == "down"
    assert "kaboom" in by_key["backup"]["detail"]
    # os outros checks (inclusive os que também tocam o banco) seguiram normais
    assert by_key["database"]["status"] in ("ok", "degraded")
    assert by_key["api"]["status"] == "ok"


@pytest.mark.asyncio
async def test_health_alert_template_renders():
    from app.shared.mailer import TEMPLATES, _env

    for bad, label, st in ((True, "Cache / Redis", "fora do ar"), (False, "Cache / Redis", "operacional")):
        html = _env.from_string(TEMPLATES["health_alert"][1]).render(
            bad=bad, service_label=label, status_pt=st, detail="sem resposta", when="01/01 00:00 UTC"
        )
        assert label in html
        assert st in html


@pytest.mark.asyncio
async def test_backup_result_template_renders():
    from app.shared.mailer import TEMPLATES, _env

    ok_html = _env.from_string(TEMPLATES["backup_result"][1]).render(
        ok=True, trigger="automático", when="01/01/2026 03:00 UTC",
        filename="backup_x.tar.gz", size_mb=5.2, with_media=True, destinations="sftp", error=None,
    )
    assert "backup_x.tar.gz" in ok_html and "5.2 MB" in ok_html

    err_html = _env.from_string(TEMPLATES["backup_result"][1]).render(
        ok=False, trigger="manual", when="01/01/2026 03:00 UTC",
        filename="x", size_mb=0, with_media=False, destinations=None, error="pg_dump falhou",
    )
    assert "pg_dump falhou" in err_html
