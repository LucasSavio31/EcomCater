"""Regra de negócio do módulo `notifications`."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.modules.notifications.models import Notification


async def create(
    db: AsyncSession,
    *,
    type: str,
    title: str,
    message: str | None = None,
    link_path: str | None = None,
    unless_types: tuple[str, ...] = (),
) -> Notification | None:
    """Cria o aviso -- UMA vez por (tipo, item): se o mesmo evento chegar de
    novo (webhook repetido, retry), devolve None e não duplica. `unless_types`:
    também não cria se o item já tem aviso de um desses tipos (ex.: "Nova
    venda" que chegou DEPOIS do "Venda paga" do mesmo pedido)."""
    if link_path:
        dup = await db.scalar(
            select(Notification.id)
            .where(Notification.type.in_((type, *unless_types)), Notification.link_path == link_path)
            .limit(1)
        )
        if dup:
            return None
    row = Notification(type=type, title=title, message=message, link_path=link_path)
    db.add(row)
    await db.flush()
    return row


async def upgrade_or_create(
    db: AsyncSession, *, from_type: str, type: str, title: str, message: str | None = None, link_path: str
) -> Notification | None:
    """Evolui o aviso anterior do mesmo item em vez de criar outro (ex.: "Nova
    venda" -> "Venda paga" do mesmo pedido): vira o tipo novo, volta a ficar
    não lido e sobe pro topo. Sem aviso anterior, cria normal."""
    if await db.scalar(
        select(Notification.id).where(Notification.type == type, Notification.link_path == link_path).limit(1)
    ):
        return None
    row = await db.scalar(
        select(Notification)
        .where(Notification.type == from_type, Notification.link_path == link_path)
        .order_by(Notification.created_at.desc())
        .limit(1)
    )
    if row is None:
        return await create(db, type=type, title=title, message=message, link_path=link_path)
    row.type, row.title, row.message = type, title, message
    row.read_at = None
    row.created_at = datetime.now(UTC)
    await db.flush()
    return row


def notification_out(row: Notification) -> dict:
    return {
        "id": str(row.id),
        "type": row.type,
        "title": row.title,
        "message": row.message,
        "link_path": row.link_path,
        "read_at": row.read_at.isoformat() if row.read_at else None,
        "created_at": row.created_at.isoformat(),
    }


async def list_recent(db: AsyncSession, *, limit: int = 50) -> list[Notification]:
    return list(
        await db.scalars(
            select(Notification).order_by(Notification.created_at.desc()).limit(limit)
        )
    )


async def unread_count(db: AsyncSession) -> int:
    return await db.scalar(
        select(func.count()).select_from(Notification).where(Notification.read_at.is_(None))
    ) or 0


async def mark_read(db: AsyncSession, notification_id: str) -> Notification:
    row = await db.get(Notification, notification_id)
    if not row:
        raise NotFoundError("Notificação não encontrada.")
    if row.read_at is None:
        row.read_at = datetime.now(UTC)
        await db.flush()
    return row


async def mark_all_read(db: AsyncSession) -> None:
    await db.execute(
        Notification.__table__.update()
        .where(Notification.read_at.is_(None))
        .values(read_at=datetime.now(UTC))
    )
    await db.flush()


async def delete_one(db: AsyncSession, notification_id: str) -> None:
    row = await db.get(Notification, notification_id)
    if not row:
        raise NotFoundError("Notificação não encontrada.")
    await db.delete(row)
    await db.flush()


async def delete_all(db: AsyncSession) -> None:
    await db.execute(delete(Notification))
    await db.flush()
