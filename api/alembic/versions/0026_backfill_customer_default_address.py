"""Backfill: endereço padrão do cliente a partir da última compra.

Revision ID: 0026_backfill_addr
Revises: 0025_cart_recovery
Create Date: 2026-08-30

Clientes que compraram como convidado (ou nunca cadastraram endereço) passam a
ter o endereço da última compra como endereço padrão — igual ao que já aparece
nos detalhes do pedido. Idempotente: só cria para quem não tem nenhum endereço.
"""
from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0026_backfill_addr"
down_revision: str | None = "0025_cart_recovery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _digits(v: str | None) -> str:
    return "".join(ch for ch in (v or "") if ch.isdigit())


def upgrade() -> None:
    tables = _tables()
    if not {"users", "orders", "customer_addresses"} <= tables:
        return

    bind = op.get_bind()
    # usuários sem nenhum endereço cadastrado
    user_ids = [
        r[0]
        for r in bind.execute(
            sa.text(
                """
                SELECT u.id FROM users u
                WHERE NOT EXISTS (
                    SELECT 1 FROM customer_addresses a WHERE a.user_id = u.id
                )
                """
            )
        )
    ]
    for uid in user_ids:
        row = bind.execute(
            sa.text(
                """
                SELECT shipping_address_json, email
                FROM orders
                WHERE user_id = :uid AND shipping_address_json IS NOT NULL
                ORDER BY placed_at DESC NULLS LAST, created_at DESC
                LIMIT 1
                """
            ),
            {"uid": uid},
        ).fetchone()
        if not row:
            continue
        addr = row[0]
        if isinstance(addr, str):
            try:
                addr = json.loads(addr)
            except ValueError:
                continue
        if not isinstance(addr, dict):
            continue

        zip_digits = _digits(addr.get("zip"))[:8]
        street = (addr.get("street") or "").strip()
        if not zip_digits or not street:
            continue

        bind.execute(
            sa.text(
                """
                INSERT INTO customer_addresses
                    (id, user_id, label, recipient_name, zip, street, number,
                     complement, district, city, state, country, is_default,
                     created_at, updated_at)
                VALUES
                    (gen_random_uuid(), :user_id, :label, :recipient_name, :zip,
                     :street, :number, :complement, :district, :city, :state,
                     :country, TRUE, now(), now())
                """
            ),
            {
                "user_id": uid,
                "label": "Endereço da última compra",
                "recipient_name": (addr.get("recipient_name") or "")[:160],
                "zip": zip_digits,
                "street": street[:200],
                "number": (str(addr.get("number") or "").strip() or "s/n")[:20],
                "complement": ((addr.get("complement") or "").strip() or None),
                "district": (addr.get("district") or "").strip()[:120],
                "city": (addr.get("city") or "").strip()[:120],
                "state": (addr.get("state") or "").strip().upper()[:2],
                "country": (addr.get("country") or "BR").strip().upper()[:2],
            },
        )


def downgrade() -> None:
    # backfill de dados — nada a desfazer com segurança
    pass
