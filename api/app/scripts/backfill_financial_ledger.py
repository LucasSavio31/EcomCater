"""Backfill do livro-caixa financeiro (menu Faturamento).

- Preenche `products.cost_cents` e `order_items.unit_cost_cents` com 13000
  (R$ 130,00) onde estiverem vazios.
- Gera os `financial_events` (placed / paid / refunded / canceled) para os
  pedidos que já existem, para que o faturamento histórico apareça no menu
  Faturamento e no painel.

Idempotente: pode rodar quantas vezes quiser.

    docker compose exec -T api python -m app.scripts.backfill_financial_ledger
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.modules.financial import service as financial
from app.modules.orders.models import Order

DEFAULT_COST_CENTS = 13000

_PAID_STATUSES = {
    "paid",
    "processing",
    "tracking_available",
    "shipped",
    "in_transit",
    "delivered",
    "refunded",  # foi pago antes de ser estornado
}


async def run() -> dict:
    async with SessionLocal() as db:
        r1 = await db.execute(
            text(
                "UPDATE products SET cost_cents = :c WHERE cost_cents IS NULL"
            ),
            {"c": DEFAULT_COST_CENTS},
        )
        r2 = await db.execute(
            text(
                "UPDATE order_items SET unit_cost_cents = :c WHERE unit_cost_cents IS NULL"
            ),
            {"c": DEFAULT_COST_CENTS},
        )
        await db.commit()

        orders = (
            await db.scalars(select(Order).options(selectinload(Order.items)))
        ).all()

        counts = {"placed": 0, "paid": 0, "refunded": 0, "canceled": 0}
        for o in orders:
            when = o.placed_at or o.created_at
            await financial.record(db, kind="placed", order=o, when=when)
            counts["placed"] += 1

            paid = o.payment_status == "paid" or o.status in _PAID_STATUSES
            if paid:
                await financial.record(db, kind="paid", order=o, when=when)
                counts["paid"] += 1
            if o.status == "refunded":
                await financial.record(
                    db, kind="refunded", order=o, when=o.updated_at or when
                )
                counts["refunded"] += 1
            if o.status == "canceled":
                await financial.record(
                    db, kind="canceled", order=o, when=o.updated_at or when
                )
                counts["canceled"] += 1
        await db.commit()

        summary = {
            "products_cost_filled": r1.rowcount,
            "order_items_cost_filled": r2.rowcount,
            "orders_scanned": len(orders),
            "events_ensured": counts,
        }
        return summary


if __name__ == "__main__":
    result = asyncio.run(run())
    print("backfill financeiro concluído:", result)
