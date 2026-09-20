"""Broadcast em tempo real do sininho do admin (venda paga, devolução
entregue, novo pedido, novo envio) via WebSocket.

In-process, sem broker: cada aba de admin conectada mantém uma fila; ao criar
uma notificação, `events.py` publica aqui e todo mundo conectado recebe na
hora -- sem depender do polling de 30s do sininho (que continua existindo
como rede de segurança caso a conexão caia).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger("notifications.stream")

_subscribers: set[asyncio.Queue[dict[str, Any]]] = set()


def subscribe() -> asyncio.Queue[dict[str, Any]]:
    q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
    _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue[dict[str, Any]]) -> None:
    _subscribers.discard(q)


def publish(event: dict[str, Any]) -> None:
    for q in list(_subscribers):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("fila cheia -- descartando evento em tempo real para 1 assinante")
