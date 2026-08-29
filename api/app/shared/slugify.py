"""Geração de slug com tratamento de acento/caractere especial + unicidade."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from slugify import slugify as _slugify


def make_slug(text: str) -> str:
    return _slugify(text, lowercase=True, max_length=200)


async def unique_slug(
    text: str,
    exists: Callable[[str], Awaitable[bool]],
) -> str:
    """`exists(slug)` deve retornar True se o slug já está em uso.

    Acrescenta sufixo -2, -3, ... até achar um livre.
    """
    base = make_slug(text) or "item"
    candidate = base
    i = 2
    while await exists(candidate):
        candidate = f"{base}-{i}"
        i += 1
    return candidate
