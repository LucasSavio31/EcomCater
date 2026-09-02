"""Monitoramento: check de backup, alerta de anomalia e resumo diário."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.modules.admin.models import EmailLog
from app.modules.system.models import BackupSettings


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
