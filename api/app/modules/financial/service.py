"""Serviço do livro-caixa financeiro (métricas cumulativas, à prova de exclusão)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import Integer, cast, extract, func, select
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


def _sum_of(col, kind: str):
    """`coalesce(sum(col) filter (where kind = :kind), 0)` — soma por tipo de fato."""
    return func.coalesce(func.sum(col).filter(FinancialEvent.kind == kind), 0)


def _count_of(kind: str):
    """`count(*) filter (where kind = :kind)` — contagem por tipo de fato."""
    return func.count().filter(FinancialEvent.kind == kind)


def bucketing(win_start: datetime, win_end: datetime) -> tuple[timedelta, int]:
    """(passo, nº de baldes) para a série temporal de um período."""
    span = max(win_end - win_start, timedelta(hours=1))
    if span <= timedelta(days=2):
        step = timedelta(hours=1)
    else:
        days = span.days + 1
        step = timedelta(days=max(1, days // 31 + (1 if days % 31 else 0)))
    n = max(1, min(60, int(span / step) + 1))
    return step, n


async def series_buckets(
    db: AsyncSession, anchor_start: datetime, step: timedelta, n: int
) -> dict[int, dict]:
    """Agrega o livro-caixa em `n` baldes de largura `step` a partir de
    `anchor_start`, numa ÚNICA query (índice do balde = floor((t - anchor)/step)).

    Retorna `{i: {...}}` só para os baldes com dados. Chaves por balde:
    `gross`, `cost`, `refunded_cents`, `canceled_cents`,
    `placed_count`, `refunded_count`, `canceled_count`.
    """
    end = anchor_start + step * n
    bi = cast(
        func.floor(
            extract("epoch", FinancialEvent.occurred_at - anchor_start) / step.total_seconds()
        ),
        Integer,
    ).label("bi")
    rows = (
        await db.execute(
            select(
                bi,
                _sum_of(FinancialEvent.gross_cents, "paid"),
                _sum_of(FinancialEvent.cost_cents, "paid"),
                _sum_of(FinancialEvent.gross_cents, "refunded"),
                _sum_of(FinancialEvent.gross_cents, "canceled"),
                _count_of("placed"),
                _count_of("refunded"),
                _count_of("canceled"),
            )
            .where(
                FinancialEvent.occurred_at >= anchor_start,
                FinancialEvent.occurred_at < end,
            )
            .group_by(bi)
        )
    ).all()
    out: dict[int, dict] = {}
    for r in rows:
        idx = int(r[0])
        if 0 <= idx < n:
            out[idx] = {
                "gross": int(r[1] or 0),
                "cost": int(r[2] or 0),
                "refunded_cents": int(r[3] or 0),
                "canceled_cents": int(r[4] or 0),
                "placed_count": int(r[5] or 0),
                "refunded_count": int(r[6] or 0),
                "canceled_count": int(r[7] or 0),
            }
    return out


async def summary(db: AsyncSession, win_start: datetime, win_end: datetime) -> dict:
    """Resumo + série temporal do período. Tudo vem do livro-caixa."""
    # agregados do período — uma query só (contadores e somas por `kind`)
    agg = (
        await db.execute(
            select(
                _count_of("placed"),
                _sum_of(FinancialEvent.gross_cents, "paid"),
                _sum_of(FinancialEvent.cost_cents, "paid"),
                _sum_of(FinancialEvent.gross_cents, "refunded"),
                _count_of("refunded"),
                _sum_of(FinancialEvent.gross_cents, "canceled"),
                _count_of("canceled"),
            ).where(
                FinancialEvent.occurred_at >= win_start,
                FinancialEvent.occurred_at <= win_end,
            )
        )
    ).one()
    orders_total = int(agg[0] or 0)
    gross = int(agg[1] or 0)
    cost = int(agg[2] or 0)
    net = gross - cost
    refunded = int(agg[3] or 0)
    refunds_count = int(agg[4] or 0)
    canceled = int(agg[5] or 0)
    canceled_count = int(agg[6] or 0)

    step, n = bucketing(win_start, win_end)
    buckets = await series_buckets(db, win_start, step, n)
    series = []
    for i in range(n):
        b0 = win_start + step * i
        b = buckets.get(i)
        g = b["gross"] if b else 0
        c = b["cost"] if b else 0
        label = b0.strftime("%d/%m") if step >= timedelta(days=1) else b0.strftime("%d/%m %Hh")
        series.append(
            {
                "label": label,
                "gross_cents": g,
                "net_cents": g - c,
                "refunded_cents": b["refunded_cents"] if b else 0,
                "canceled_cents": b["canceled_cents"] if b else 0,
                "orders": b["placed_count"] if b else 0,
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
