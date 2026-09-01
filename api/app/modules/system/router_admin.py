"""Rotas de `system`: saúde da infra + backup/restauração."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin, require_role
from app.core.errors import NotFoundError, ValidationError
from app.modules.admin.models import AdminUser
from app.modules.system import service_backup as backup
from app.modules.system.service_health import run_checks

admin_router = APIRouter()
public_router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]
SuperDep = Annotated[AdminUser, Depends(require_role("super_admin"))]


# ------------------------------------------------------------------ saúde
@admin_router.get("/health")
async def health(db: DbDep, _: AdminDep) -> list[dict]:
    return await run_checks(db)


@admin_router.get("/health/history")
async def health_history(
    db: DbDep,
    _: AdminDep,
    date_from: str = Query(alias="from"),
    date_to: str = Query(alias="to"),
    key: str | None = Query(default=None),
) -> list[dict]:
    from datetime import UTC, datetime, timedelta

    from app.modules.system.service_health import history

    def _parse(s: str, end: bool) -> datetime:
        try:
            d = datetime.fromisoformat(s)
        except ValueError as exc:
            raise ValidationError("Data inválida (use AAAA-MM-DD).") from exc
        if d.tzinfo is None:
            d = d.replace(tzinfo=UTC)
        if end and len(s) <= 10:
            d = d + timedelta(days=1) - timedelta(microseconds=1)
        return d

    return await history(db, since=_parse(date_from, False), until=_parse(date_to, True), service_key=key)


# ------------------------------------------------------------------ backup
class BackupSettingsIn(BaseModel):
    auto_enabled: bool | None = None
    frequency: str | None = None
    hour: int | None = None
    keep: int | None = None
    include_media: bool | None = None
    folder_path: str | None = None
    sftp: dict | None = None
    gdrive: dict | None = None


@admin_router.get("/backup/settings")
async def get_backup_settings(db: DbDep, _: AdminDep) -> dict:
    return backup.settings_out(await backup.get_settings_row(db))


@admin_router.patch("/backup/settings")
async def patch_backup_settings(body: BackupSettingsIn, db: DbDep, _: SuperDep) -> dict:
    if body.frequency and body.frequency not in ("diario", "semanal", "mensal"):
        raise ValidationError("Frequência inválida.")
    if body.hour is not None and not (0 <= body.hour <= 23):
        raise ValidationError("Hora deve estar entre 0 e 23.")
    row = await backup.update_settings(db, body.model_dump(exclude_unset=True))
    await db.commit()
    return backup.settings_out(row)


@admin_router.get("/backup")
async def list_backups(db: DbDep, _: AdminDep) -> list[dict]:
    return await backup.list_records(db)


@admin_router.post("/backup/run", status_code=status.HTTP_201_CREATED)
async def run_backup(db: DbDep, _: SuperDep, include_media: bool | None = Query(default=None)) -> dict:
    rec = await backup.create_backup(db, triggered_by="manual", include_media=include_media)
    if rec.status == "error":
        raise ValidationError(f"Backup falhou: {rec.error_message}")
    return backup.record_out(rec)


@admin_router.get("/backup/{record_id}/download")
async def download_backup(record_id: str, db: DbDep, _: SuperDep) -> FileResponse:
    try:
        path, filename = await backup.resolve_path(db, record_id)
    except FileNotFoundError as exc:
        raise NotFoundError(str(exc)) from exc
    return FileResponse(path, filename=filename, media_type="application/gzip")


@admin_router.delete("/backup/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backup(record_id: str, db: DbDep, _: SuperDep) -> None:
    await backup.delete_record(db, record_id)


@admin_router.post("/backup/restore")
async def restore_backup(
    db: DbDep,
    _: SuperDep,
    file: Annotated[UploadFile, File()],
    confirm: Annotated[str, Form()] = "",
) -> dict:
    if confirm.strip().upper() != "RESTAURAR":
        raise ValidationError('Digite "RESTAURAR" para confirmar a operação.')
    raw = await file.read()
    if not raw:
        raise ValidationError("Arquivo vazio.")
    try:
        return await backup.restore_from_upload(
            db, raw, file.filename or "upload.bin", confirm=True
        )
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


# ----------------------------------------------------- agendamento (cron externo)
@public_router.post("/backup/cron")
async def backup_cron(db: DbDep, token: str = Query(...)) -> dict:
    from app.core.config import settings

    if token != settings.system_cron_token:
        raise NotFoundError("Not found")
    return await backup.run_scheduled(db)
