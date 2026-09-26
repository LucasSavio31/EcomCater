"""Redirecionamento de slug antigo de produto + tira nomes de marca de terceiros
dos modelos (política do Google Merchant Center: marca registrada alheia no
título/cor derruba anúncio e arrisca suspensão da conta).

- cria `product_slug_redirects` (slug antigo -> produto; a loja responde 301);
- renomeia, em nome/cor/descrições/SEO/alt de imagem/especificações:
  FERRARI -> VERMELHO, MULTICAN/MULTICAM -> CAMUFLADO,
  FAIRBANKS -> 3010, ROAD -> 3020, INTRUDER -> 3030
  (os demais modelos já usam código numérico; SKU fica como está -- ERP/
  fornecedor casam por ele). Pedidos já feitos NÃO são tocados (snapshot).

Revision ID: 0083_product_slug_redirects
Revises: 0082_financial_payment_method
Create Date: 2026-09-26

Idempotente: só pega produto cujo NOME ainda tem uma das palavras.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

import sqlalchemy as sa
from slugify import slugify
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0083_product_slug_redirects"
down_revision: str | None = "0082_financial_payment_method"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_RENAMES = {
    "ferrari": "vermelho",
    "multican": "camuflado",
    "multicam": "camuflado",
    "fairbanks": "3010",
    "road": "3020",
    "intruder": "3030",
}
_WORD_RE = re.compile(r"\b(" + "|".join(_RENAMES) + r")\b", re.IGNORECASE)


def _swap(text: str | None) -> str | None:
    if not text:
        return text

    def repl(m: re.Match) -> str:
        word, new = m.group(0), _RENAMES[m.group(0).lower()]
        if word.isupper():
            return new.upper()
        if word[:1].isupper():
            return new[:1].upper() + new[1:]
        return new

    return _WORD_RE.sub(repl, text)


def upgrade() -> None:
    bind = op.get_bind()
    if "product_slug_redirects" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "product_slug_redirects",
            sa.Column("old_slug", sa.String(260), primary_key=True),
            sa.Column(
                "product_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("products.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_product_slug_redirects_product_id", "product_slug_redirects", ["product_id"])

    rows = bind.execute(
        sa.text(
            "SELECT id, name, slug, color_name, short_description, description, seo_title, seo_description "
            "FROM products WHERE name ~* :pat"
        ),
        {"pat": r"\m(" + "|".join(_RENAMES) + r")\M"},
    ).mappings().all()

    for r in rows:
        new_name = _swap(r["name"])
        base = slugify(new_name, lowercase=True, max_length=200) or "produto"
        new_slug, i = base, 2
        while bind.execute(
            sa.text("SELECT 1 FROM products WHERE slug = :s AND id <> :id"), {"s": new_slug, "id": r["id"]}
        ).first():
            new_slug = f"{base}-{i}"
            i += 1

        bind.execute(
            sa.text(
                "UPDATE products SET name = :name, slug = :slug, color_name = :color, "
                "short_description = :short, description = :descr, seo_title = :st, seo_description = :sd "
                "WHERE id = :id"
            ),
            {
                "id": r["id"], "name": new_name, "slug": new_slug, "color": _swap(r["color_name"]),
                "short": _swap(r["short_description"]), "descr": _swap(r["description"]),
                "st": _swap(r["seo_title"]), "sd": _swap(r["seo_description"]),
            },
        )
        if new_slug != r["slug"]:
            bind.execute(
                sa.text(
                    "INSERT INTO product_slug_redirects (old_slug, product_id) VALUES (:old, :id) "
                    "ON CONFLICT (old_slug) DO UPDATE SET product_id = EXCLUDED.product_id"
                ),
                {"old": r["slug"], "id": r["id"]},
            )
            bind.execute(sa.text("DELETE FROM product_slug_redirects WHERE old_slug = :s"), {"s": new_slug})

        for img in bind.execute(
            sa.text("SELECT id, alt FROM product_images WHERE product_id = :id AND alt IS NOT NULL"), {"id": r["id"]}
        ).mappings().all():
            if _swap(img["alt"]) != img["alt"]:
                bind.execute(
                    sa.text("UPDATE product_images SET alt = :alt WHERE id = :id"),
                    {"alt": _swap(img["alt"]), "id": img["id"]},
                )
        for spec in bind.execute(
            sa.text("SELECT id, value FROM product_specs WHERE product_id = :id"), {"id": r["id"]}
        ).mappings().all():
            if _swap(spec["value"]) != spec["value"]:
                bind.execute(
                    sa.text("UPDATE product_specs SET value = :v WHERE id = :id"),
                    {"v": _swap(spec["value"]), "id": spec["id"]},
                )


def downgrade() -> None:
    # Não desfaz a renomeação (nome de marca alheia não deve voltar); só a tabela.
    if "product_slug_redirects" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("product_slug_redirects")
