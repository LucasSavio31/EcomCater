"""Helpers de busca textual — comparação ILIKE ignorando acentos.

Todo campo de busca/filtro do site deve casar com ou sem acento
("acucar" == "açúcar", "sao paulo" == "São Paulo"). A extensão
`unaccent` do Postgres é criada pela migration 0054.
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.sql.elements import ColumnElement


def _u(expr):  # noqa: ANN001
    return func.unaccent(expr)


def ilike_unaccent(column, term: str) -> ColumnElement[bool]:  # noqa: ANN001
    """`column ILIKE %term%` com acentos removidos dos dois lados."""
    return _u(column).ilike(_u(f"%{term}%"))


def like_pattern_unaccent(column, pattern: str) -> ColumnElement[bool]:  # noqa: ANN001
    """Como `ilike_unaccent`, mas o pattern já vem pronto (com `%`)."""
    return _u(column).ilike(_u(pattern))
