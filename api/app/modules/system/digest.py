"""Resumo diário por e-mail para o admin: pedidos, faturamento e saúde.

Disparado 1x/dia pelo tick do agendador de backup (já roda a cada 10 min com
trava de worker único). Idempotente via flag no Redis por data local.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import redis_client
from app.shared.timez import local_today_start, store_tz

logger = logging.getLogger("system.digest")


async def _already_sent_today(day: str) -> bool:
    try:
        # SET NX: devolve True se conseguiu setar (ou seja, ainda NÃO tinha sido enviado)
        got = await redis_client.set(f"ecom:digest:sent:{day}", "1", nx=True, ex=26 * 3600)
        return not got
    except Exception:  # noqa: BLE001
        return False  # sem Redis: melhor mandar do que engolir


async def maybe_send_daily_digest(db: AsyncSession) -> bool:
    if not settings.daily_digest_enabled:
        return False
    now_local = datetime.now(store_tz())
    if now_local.hour < settings.daily_digest_hour:
        return False
    day = now_local.strftime("%Y-%m-%d")
    if await _already_sent_today(day):
        return False
    await send_daily_digest(db, label=now_local.strftime("%d/%m/%Y"))
    return True


async def send_daily_digest(db: AsyncSession, *, label: str | None = None) -> None:
    from app.modules.orders.models import Order
    from app.modules.system.models import BackupSettings
    from app.modules.system.service_health import run_checks
    from app.shared import mailer

    start = local_today_start()
    orders = int(await db.scalar(select(func.count()).where(Order.placed_at >= start)) or 0)
    paid = int(
        await db.scalar(
            select(func.count()).where(Order.placed_at >= start, Order.payment_status == "paid")
        )
        or 0
    )
    pending = int(
        await db.scalar(select(func.count()).where(Order.status == "pending_payment")) or 0
    )
    revenue = int(
        await db.scalar(
            select(func.coalesce(func.sum(Order.grand_total_cents), 0)).where(
                Order.placed_at >= start, Order.payment_status == "paid"
            )
        )
        or 0
    )

    # snapshot de saúde (sem persistir de novo)
    checks = await run_checks(db, persist=False)
    services = [
        {
            "label": c["label"],
            "status_pt": mailer.STATUS_PT.get(c["status"], c["status"]),
            "detail": c.get("detail"),
        }
        for c in checks
    ]

    bkp = await db.get(BackupSettings, 1)
    last_backup = None
    if bkp and bkp.last_run_at:
        lr = bkp.last_run_at
        if lr.tzinfo is None:
            lr = lr.replace(tzinfo=UTC)
        last_backup = f"{lr.strftime('%d/%m/%Y %H:%M UTC')} ({bkp.last_status or '?'})"

    await mailer.send(
        db,
        to=await mailer.admin_notify_email(db),
        template="daily_digest",
        context={
            "date": label or datetime.now(store_tz()).strftime("%d/%m/%Y"),
            "orders": orders,
            "paid": paid,
            "pending": pending,
            "revenue_cents": revenue,
            "services": services,
            "last_backup": last_backup,
        },
    )
    await db.commit()
