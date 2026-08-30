"""Subscribers de eventos de cliente → e-mail transacional de boas-vindas."""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.events import on
from app.modules.admin.models import StoreSettings
from app.modules.customers.models import User
from app.shared import mailer

logger = logging.getLogger("customers.events")


@on("customer.registered")
async def _on_registered(payload: dict) -> None:
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.id == payload["user_id"]))
        if not user or not user.email:
            return
        store = await db.get(StoreSettings, 1)
        await mailer.send(
            db,
            to=user.email,
            template="account_created",
            context={"store_name": (store.store_name if store else None) or "nossa loja"},
        )
        await db.commit()
