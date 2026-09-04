"""Backup e restauração do sistema.

Um backup é um arquivo `.tar.gz` contendo:
  - `database.dump`  -> pg_dump formato custom (-F c) do banco inteiro
  - `media/...`       -> árvore de arquivos de mídia (se incluída)
  - `manifest.json`   -> metadados (data, versão do schema, flags)

Restaurar aceita tanto o `.tar.gz` quanto um `.dump` cru (só o banco).
O agendamento segue o padrão do projeto: um cron externo chama
`POST /api/system/backup/cron?token=...`; o endpoint decide se está na hora.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.system.models import BackupRecord, BackupSettings

logger = logging.getLogger("system.backup")

_TRIGGERS_PRUNED = {"manual", "auto"}


# --------------------------------------------------------------- infra helpers
def backup_dir() -> Path:
    p = Path(settings.backup_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _pg_tool(name: str) -> str:
    if settings.pg_bin_dir:
        cand = Path(settings.pg_bin_dir) / name
        if cand.exists() or cand.with_suffix(".exe").exists():
            return str(cand)
    found = shutil.which(name)
    if found:
        return found
    # fallback do ambiente de dev desta máquina (Postgres portátil)
    for guess in (r"C:\Users\lsavy\pgsql\pgsql\bin", "/usr/bin", "/usr/lib/postgresql/16/bin"):
        cand = Path(guess) / name
        if cand.exists() or cand.with_suffix(".exe").exists():
            return str(cand)
    return name  # deixa o PATH resolver (e falhar com erro claro)


def _pg_conn_parts() -> tuple[dict, str]:
    parsed = urlparse(settings.database_url.replace("postgresql+asyncpg", "postgresql"))
    env = {**os.environ}
    if parsed.password:
        env["PGPASSWORD"] = parsed.password
    args = [
        "-h", parsed.hostname or "localhost",
        "-p", str(parsed.port or 5432),
        "-U", parsed.username or "postgres",
    ]
    dbname = parsed.path.lstrip("/")
    return {"env": env, "args": args, "host": parsed.hostname or "localhost",
            "port": parsed.port or 5432, "user": parsed.username or "postgres",
            "password": parsed.password}, dbname


def _dump_database(dest: Path) -> None:
    parts, dbname = _pg_conn_parts()
    cmd = [_pg_tool("pg_dump"), *parts["args"], "-F", "c", "--no-owner", "--no-privileges",
           "-f", str(dest), dbname]
    res = subprocess.run(cmd, env=parts["env"], capture_output=True, text=True, timeout=600)
    if res.returncode != 0:
        raise RuntimeError(f"pg_dump falhou: {res.stderr.strip()}")


_IGNORABLE_RESTORE = ("unrecognized configuration parameter", "must be owner of extension",
                      "already exists")


def _only_ignorable(stderr: str) -> bool:
    errs = [ln for ln in stderr.splitlines() if "pg_restore: error:" in ln]
    return bool(errs) and all(any(p in ln for p in _IGNORABLE_RESTORE) for ln in errs)


def _terminate_other_connections() -> None:
    import psycopg2  # driver síncrono, já disponível via alembic/psycopg2-binary

    parts, dbname = _pg_conn_parts()
    conn = psycopg2.connect(host=parts["host"], port=parts["port"], user=parts["user"],
                            password=parts["password"], dbname="postgres")
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (dbname,),
            )
    finally:
        conn.close()


def _restore_database(dump_path: Path) -> None:
    parts, dbname = _pg_conn_parts()
    _terminate_other_connections()
    cmd = [_pg_tool("pg_restore"), *parts["args"], "-d", dbname,
           "--clean", "--if-exists", "--no-owner", "--no-privileges", str(dump_path)]
    res = subprocess.run(cmd, env=parts["env"], capture_output=True, text=True, timeout=900)
    if res.returncode != 0 and not _only_ignorable(res.stderr):
        raise RuntimeError(f"pg_restore falhou: {res.stderr.strip()}")


# --------------------------------------------------------------- destinos extra
def _copy_to_folder(archive: Path, folder: str) -> dict:
    dst = Path(folder)
    if not dst.is_dir():
        return {"type": "folder", "ok": False, "detail": f"pasta inacessível: {folder}"}
    shutil.copy2(archive, dst / archive.name)
    return {"type": "folder", "ok": True, "detail": str(dst / archive.name)}


def _copy_to_sftp(archive: Path, cfg: dict) -> dict:
    try:
        import paramiko  # type: ignore
    except Exception:  # noqa: BLE001
        return {"type": "sftp", "ok": False, "detail": "paramiko não instalado no servidor"}
    try:
        transport = paramiko.Transport((cfg["host"], int(cfg.get("port") or 22)))
        pkey = None
        if cfg.get("key_path"):
            pkey = paramiko.RSAKey.from_private_key_file(cfg["key_path"])
        transport.connect(username=cfg.get("user"), password=cfg.get("password") or None, pkey=pkey)
        sftp = paramiko.SFTPClient.from_transport(transport)
        remote_dir = cfg.get("remote_dir") or "."
        remote = f"{remote_dir.rstrip('/')}/{archive.name}"
        sftp.put(str(archive), remote)
        sftp.close()
        transport.close()
        return {"type": "sftp", "ok": True, "detail": remote}
    except Exception as exc:  # noqa: BLE001
        return {"type": "sftp", "ok": False, "detail": str(exc)}


def _copy_to_gdrive(archive: Path, cfg: dict) -> dict:
    sa_path = cfg.get("service_account_json_path")
    if not sa_path or not Path(sa_path).is_file():
        return {"type": "gdrive", "ok": False,
                "detail": "credencial ausente: informe o caminho do JSON da conta de serviço"}
    try:
        from google.oauth2 import service_account  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
        from googleapiclient.http import MediaFileUpload  # type: ignore
    except Exception:  # noqa: BLE001
        return {"type": "gdrive", "ok": False,
                "detail": "bibliotecas do Google não instaladas no servidor"}
    try:
        creds = service_account.Credentials.from_service_account_file(
            sa_path, scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        meta = {"name": archive.name}
        if cfg.get("folder_id"):
            meta["parents"] = [cfg["folder_id"]]
        media = MediaFileUpload(str(archive), resumable=False)
        f = drive.files().create(body=meta, media_body=media, fields="id").execute()
        return {"type": "gdrive", "ok": True, "detail": f"file_id={f.get('id')}"}
    except Exception as exc:  # noqa: BLE001
        return {"type": "gdrive", "ok": False, "detail": str(exc)}


async def _run_destinations(archive: Path, cfg: BackupSettings) -> list[dict]:
    results: list[dict] = []
    if cfg.folder_path:
        results.append(_copy_to_folder(archive, cfg.folder_path))
    if (cfg.sftp_json or {}).get("enabled"):
        results.append(_copy_to_sftp(archive, cfg.sftp_json))
    if (cfg.gdrive_json or {}).get("enabled"):
        results.append(_copy_to_gdrive(archive, cfg.gdrive_json))
    return results


# --------------------------------------------------------------- API pública
async def get_settings_row(db: AsyncSession) -> BackupSettings:
    row = await db.get(BackupSettings, 1)
    if not row:
        row = BackupSettings(id=1, updated_at=datetime.now(UTC))
        db.add(row)
        await db.flush()
    return row


def settings_out(row: BackupSettings) -> dict:
    def _mask(d: dict, keys: tuple[str, ...]) -> dict:
        d = dict(d or {})
        for k in keys:
            if d.get(k):
                d[k] = "********"
        return d

    return {
        "auto_enabled": row.auto_enabled,
        "frequency": row.frequency,
        "hour": row.hour,
        "keep": row.keep,
        "include_media": row.include_media,
        "folder_path": row.folder_path,
        "sftp": _mask(row.sftp_json, ("password",)),
        "gdrive": dict(row.gdrive_json or {}),
        "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
        "last_status": row.last_status,
    }


def _merge_secret(current: dict, incoming: dict, keys: tuple[str, ...]) -> dict:
    """Mantém o segredo atual quando o front reenvia o valor mascarado."""
    out = dict(incoming or {})
    for k in keys:
        if out.get(k) in (None, "", "********"):
            if (current or {}).get(k):
                out[k] = current[k]
            else:
                out.pop(k, None)
    return out


async def update_settings(db: AsyncSession, data: dict) -> BackupSettings:
    row = await get_settings_row(db)
    for f in ("auto_enabled", "frequency", "hour", "keep", "include_media", "folder_path"):
        if f in data and data[f] is not None:
            setattr(row, f, data[f])
    if "sftp" in data and data["sftp"] is not None:
        row.sftp_json = _merge_secret(row.sftp_json, data["sftp"], ("password",))
    if "gdrive" in data and data["gdrive"] is not None:
        row.gdrive_json = dict(data["gdrive"])
    row.updated_at = datetime.now(UTC)
    await db.flush()
    return row


def record_out(r: BackupRecord) -> dict:
    return {
        "id": str(r.id),
        "filename": r.filename,
        "size_bytes": r.size_bytes,
        "size_mb": round((r.size_bytes or 0) / (1024 * 1024), 2),
        "status": r.status,
        "error_message": r.error_message,
        "triggered_by": r.triggered_by,
        "includes_media": r.includes_media,
        "destinations": r.destinations_json or [],
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


async def _reconcile_orphans(db: AsyncSession) -> None:
    """Recria registros para arquivos .tar.gz no disco sem linha no banco — ex.:
    o backup de segurança feito antes de uma restauração (a restauração
    sobrescreve a tabela `backup_records`, mas o arquivo continua no disco)."""
    known = {r.filename for r in await db.scalars(select(BackupRecord))}
    changed = False
    for f in sorted(backup_dir().glob("backup_*.tar.gz")):
        if f.name in known:
            continue
        from datetime import datetime as _dt

        db.add(
            BackupRecord(
                filename=f.name,
                size_bytes=f.stat().st_size,
                status="ok",
                triggered_by="import",
                includes_media=True,
                created_at=_dt.fromtimestamp(f.stat().st_mtime, tz=UTC),
            )
        )
        changed = True
    if changed:
        await db.commit()


async def list_records(db: AsyncSession) -> list[dict]:
    await _reconcile_orphans(db)
    rows = await db.scalars(select(BackupRecord).order_by(BackupRecord.created_at.desc()).limit(100))
    return [record_out(r) for r in rows]


async def _prune(db: AsyncSession, keep: int) -> None:
    rows = list(
        await db.scalars(
            select(BackupRecord)
            .where(BackupRecord.triggered_by.in_(_TRIGGERS_PRUNED), BackupRecord.status == "ok")
            .order_by(BackupRecord.created_at.desc())
        )
    )
    for old in rows[max(keep, 1):]:
        f = backup_dir() / old.filename
        if f.exists():
            f.unlink()
        await db.delete(old)


async def create_backup(db: AsyncSession, *, triggered_by: str = "manual",
                        include_media: bool | None = None) -> BackupRecord:
    cfg = await get_settings_row(db)
    with_media = cfg.include_media if include_media is None else include_media
    ts = datetime.now(UTC).strftime("%Y-%m-%d_%H-%M-%S-%f")
    name = f"backup_{ts}.tar.gz"
    archive = backup_dir() / name
    rec = BackupRecord(filename=name, status="running", triggered_by=triggered_by,
                       includes_media=with_media, created_at=datetime.now(UTC))
    db.add(rec)
    await db.flush()

    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dump = tmp_path / "database.dump"
            _dump_database(dump)
            manifest = {
                "created_at": datetime.now(UTC).isoformat(),
                "includes_media": with_media,
                "app": "ecom",
            }
            (tmp_path / "manifest.json").write_text(json.dumps(manifest, indent=2))
            with tarfile.open(archive, "w:gz") as tar:
                tar.add(dump, arcname="database.dump")
                tar.add(tmp_path / "manifest.json", arcname="manifest.json")
                media_root = Path(settings.storage_local_dir)
                if with_media and media_root.is_dir():
                    tar.add(media_root, arcname="media")
        rec.size_bytes = archive.stat().st_size
        rec.status = "ok"
        rec.destinations_json = await _run_destinations(archive, cfg)
    except Exception as exc:  # noqa: BLE001
        rec.status = "error"
        rec.error_message = str(exc)
        if archive.exists():
            archive.unlink()

    cfg.last_run_at = datetime.now(UTC)
    cfg.last_status = rec.status
    await db.flush()
    if rec.status == "ok" and triggered_by in _TRIGGERS_PRUNED:
        await _prune(db, cfg.keep)

    # avisa o admin de TODO backup (auto/manual), bem-sucedido ou com erro
    if triggered_by in ("auto", "manual"):
        try:
            from app.shared import mailer

            await mailer.send(
                db,
                to=await mailer.admin_notify_email(db),
                template="backup_result",
                context={
                    "ok": rec.status == "ok",
                    "trigger": "automático" if triggered_by == "auto" else "manual",
                    "when": rec.created_at.strftime("%d/%m/%Y %H:%M UTC"),
                    "filename": rec.filename,
                    "size_mb": round(rec.size_bytes / 1048576, 2),
                    "with_media": rec.includes_media,
                    "destinations": ", ".join(
                        d.get("kind", "?") for d in (rec.destinations_json or [])
                    )
                    or None,
                    "error": rec.error_message,
                },
            )
        except Exception:  # noqa: BLE001
            logger.warning("não foi possível avisar o admin sobre o backup", exc_info=True)

    await db.commit()
    return rec


async def delete_record(db: AsyncSession, record_id: str) -> None:
    rec = await db.get(BackupRecord, uuid.UUID(record_id))
    if not rec:
        return
    f = backup_dir() / rec.filename
    if f.exists():
        f.unlink()
    await db.delete(rec)
    await db.commit()


async def resolve_path(db: AsyncSession, record_id: str) -> tuple[Path, str]:
    rec = await db.get(BackupRecord, uuid.UUID(record_id))
    if not rec:
        raise FileNotFoundError("Backup não encontrado.")
    f = backup_dir() / rec.filename
    if not f.is_file():
        raise FileNotFoundError("Arquivo do backup não está mais no servidor.")
    return f, rec.filename


async def restore_from_upload(db: AsyncSession, raw: bytes, filename: str, *, confirm: bool) -> dict:
    if not confirm:
        raise ValueError("Restauração não confirmada.")
    # 1) backup de segurança antes de sobrescrever
    safety = await create_backup(db, triggered_by="pre-restore", include_media=True)

    from app.core.database import engine

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        upload = tmp_path / filename
        upload.write_bytes(raw)

        if tarfile.is_tarfile(upload):
            with tarfile.open(upload) as tar:
                # filter="data": bloqueia path traversal / links absolutos no tar
                tar.extractall(tmp_path, filter="data")
            dump = tmp_path / "database.dump"
            if not dump.is_file():
                raise ValueError("Arquivo .tar.gz sem 'database.dump' dentro.")
            media_dir = tmp_path / "media"
        else:
            dump = upload
            media_dir = None

        await engine.dispose()  # libera o pool antes do --clean
        _restore_database(dump)

        if media_dir and media_dir.is_dir():
            dst = Path(settings.storage_local_dir)
            dst.mkdir(parents=True, exist_ok=True)
            for item in media_dir.iterdir():
                target = dst / item.name
                if item.is_dir():
                    shutil.rmtree(target, ignore_errors=True)
                    shutil.copytree(item, target)
                else:
                    shutil.copy2(item, target)

    return {"ok": True, "safety_backup_id": str(safety.id), "safety_backup_file": safety.filename}


# --------------------------------------------------------------- agendamento
def _store_now() -> datetime:
    """Agora no fuso da loja (a 'hora' configurada é local, não UTC)."""
    from zoneinfo import ZoneInfo

    try:
        return datetime.now(ZoneInfo(settings.store_timezone))
    except Exception:  # noqa: BLE001 - fuso inválido -> cai para UTC
        return datetime.now(UTC)


def is_due(cfg: BackupSettings, now: datetime | None = None) -> bool:
    """Roda 1x por período (diário/semanal/mensal) na hora local configurada
    (`cfg.hour`). Compara por DATA local, não por horas corridas desde
    `last_run_at` — um backup MANUAL feito fora da janela (ex.: 15h) não pode
    empurrar o próximo automático pro dia seguinte só porque ainda não fez 20h
    corridas. Se ficar muito atrasado (o processo esteve fora do ar durante a
    janela inteira, por um redeploy por exemplo), roda no próximo tick mesmo
    fora da hora — não fica esperando o dia seguinte de novo."""
    if not cfg.auto_enabled:
        return False
    local = now or _store_now()
    if not cfg.last_run_at:
        return local.hour == cfg.hour
    last_local = cfg.last_run_at.astimezone(local.tzinfo)
    days_since = (local.date() - last_local.date()).days
    normal_days, catchup_days = {"semanal": (6, 9), "mensal": (27, 33)}.get(
        cfg.frequency, (1, 2)  # diário
    )
    if days_since >= catchup_days:
        return True  # muito atrasado: não espera a janela de novo
    if local.hour != cfg.hour:
        return False
    return days_since >= normal_days


async def run_scheduled(db: AsyncSession) -> dict:
    cfg = await get_settings_row(db)
    if not is_due(cfg):
        return {"ran": False, "reason": "fora da janela agendada"}
    rec = await create_backup(db, triggered_by="auto")
    return {"ran": True, "status": rec.status, "file": rec.filename}
