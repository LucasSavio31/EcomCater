"""Serviço do livro-caixa financeiro (métricas cumulativas, à prova de exclusão)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.financial.models import FinancialEvent


async def _order_amounts(db: AsyncSession, order) -> tuple[int, int, int]:
    """(gross_cents, cost_cents, items_count) de um Order já carregado com items."""
    from app.modules.products.models import Product

    gross = int(order.grand_total_cents or 0)
    items = list(order.items)
    n = sum(int(i.quantity or 0) for i in items)

    # custo: snapshot do item; senão o custo atual do produto
    missing = [i.product_id for i in items if i.unit_cost_cents is None and i.product_id]
    prod_cost: dict = {}
    if missing:
        for pid, c in (
            await db.execute(select(Product.id, Product.cost_cents).where(Product.id.in_(missing)))
        ).all():
            prod_cost[pid] = c or 0
    cost = 0
    for i in items:
        unit = i.unit_cost_cents
        if unit is None:
            unit = prod_cost.get(i.product_id, 0)
        cost += int(unit or 0) * int(i.quantity or 0)
    return gross, cost, n


async def record(db: AsyncSession, *, kind: str, order, when: datetime | None = None) -> None:
    """Grava um fato financeiro. Idempotente por (order_number, kind)."""
    exists = await db.scalar(
        select(FinancialEvent.id).where(
            FinancialEvent.order_number == order.number, FinancialEvent.kind == kind
        )
    )
    if exists:
        return
    gross, cost, n = await _order_amounts(db, order)
    db.add(
        FinancialEvent(
            occurred_at=when or datetime.now(UTC),
            kind=kind,
            order_number=order.number,
            order_id=order.id,
            gross_cents=gross,
            cost_cents=cost,
            items_count=n,
            created_at=datetime.now(UTC),
        )
    )


def _bucketing(win_start: datetime, win_end: datetime) -> tuple[timedelta, int]:
    span = max(win_end - win_start, timedelta(hours=1))
    if span <= timedelta(days=2):
        step = timedelta(hours=1)
    else:
        days = span.days + 1
        step = timedelta(days=max(1, days // 31 + (1 if days % 31 else 0)))
    n = max(1, min(60, int(span / step) + 1))
    return step, n


async def summary(db: AsyncSession, win_start: datetime, win_end: datetime) -> dict:
    """Resumo + série temporal do período. Tudo vem do livro-caixa."""

    def _win(q):
        return q.where(
            FinancialEvent.occurred_at >= win_start, FinancialEvent.occurred_at <= win_end
        )

    async def _sum(kind: str, col):
        return int(
            await db.scalar(
                _win(select(func.coalesce(func.sum(col), 0))).where(FinancialEvent.kind == kind)
            )
            or 0
        )

    async def _count(kind: str):
        return int(
            await db.scalar(
                _win(select(func.count())).select_from(FinancialEvent).where(
                    FinancialEvent.kind == kind
                )
            )
            or 0
        )

    orders_total = await _count("placed")
    gross = await _sum("paid", FinancialEvent.gross_cents)
    cost = await _sum("paid", FinancialEvent.cost_cents)
    net = gross - cost
    refunded = await _sum("refunded", FinancialEvent.gross_cents)
    refunds_count = await _count("refunded")
    canceled = await _sum("canceled", FinancialEvent.gross_cents)
    canceled_count = await _count("canceled")

    step, n = _bucketing(win_start, win_end)
    series = []
    for i in range(n):
        b0 = win_start + step * i
        b1 = b0 + step
        row = (
            await db.execute(
                select(
                    func.coalesce(
                        func.sum(FinancialEvent.gross_cents).filter(FinancialEvent.kind == "paid"),
                        0,
                    ),
                    func.coalesce(
                        func.sum(FinancialEvent.cost_cents).filter(FinancialEvent.kind == "paid"),
                        0,
                    ),
                    func.coalesce(
                        func.sum(FinancialEvent.gross_cents).filter(
                            FinancialEvent.kind == "refunded"
                        ),
                        0,
                    ),
                    func.coalesce(
                        func.sum(FinancialEvent.gross_cents).filter(
                            FinancialEvent.kind == "canceled"
                        ),
                        0,
                    ),
                    func.count().filter(FinancialEvent.kind == "placed"),
                ).where(FinancialEvent.occurred_at >= b0, FinancialEvent.occurred_at < b1)
            )
        ).one()
        label = b0.strftime("%d/%m") if step >= timedelta(days=1) else b0.strftime("%d/%m %Hh")
        series.append(
            {
                "label": label,
                "gross_cents": int(row[0] or 0),
                "net_cents": int((row[0] or 0) - (row[1] or 0)),
                "refunded_cents": int(row[2] or 0),
                "canceled_cents": int(row[3] or 0),
                "orders": int(row[4] or 0),
            }
        )

    return {
        "orders_total": orders_total,
        "gross_cents": gross,
        "cost_cents": cost,
        "net_cents": net,
        "margin_pct": round(net / gross * 100, 1) if gross else 0.0,
        "refunded_cents": refunded,
        "refunds_count": refunds_count,
        "canceled_cents": canceled,
        "canceled_count": canceled_count,
        "series": series,
    }


async def window_totals(db: AsyncSession, win_start: datetime, win_end: datetime) -> dict:
    """Só os agregados (sem série) — usado pelo dashboard."""
    s = await summary(db, win_start, win_end)
    return {k: v for k, v in s.items() if k != "series"}
