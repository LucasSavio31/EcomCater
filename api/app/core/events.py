"""Event bus in-process, assíncrono e simples.

Módulos publicam eventos de domínio (`order.paid`, `payment.confirmed`, ...) e
outros módulos assinam sem acoplamento direto. Handlers rodam em sequência; um
handler que falha é logado e não interrompe os demais.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger("events")

Handler = Callable[[dict[str, Any]], Awaitable[None]]

_subscribers: dict[str, list[Handler]] = defaultdict(list)


def subscribe(event: str, handler: Handler) -> None:
    _subscribers[event].append(handler)


def on(event: str) -> Callable[[Handler], Handler]:
    def deco(fn: Handler) -> Handler:
        subscribe(event, fn)
        return fn

    return deco


async def emit(event: str, payload: dict[str, Any] | None = None) -> None:
    data = payload or {}
    for handler in list(_subscribers.get(event, [])):
        try:
            await handler(data)
        except Exception:  # noqa: BLE001
            logger.exception("handler falhou para evento %s", event)
