"""Rotina interna de sincronização de rastreio com o Melhor Envio.

Roda dentro do processo da API (uma task asyncio) e, a cada
`me_poll_interval_seconds`, chama `poll_melhor_envio_tracking` — que consulta o
ME para todos os pedidos com etiqueta associada, preenche o código de rastreio e
avança o status do pedido (`em separação` → `rastreio disponível` → `enviado` →
`entregue`).

É complementar (e idempotente) com o webhook de rastreio do Melhor Envio.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.core.database import SessionLocal

logger = logging.getLogger("shipping.scheduler")

_task: asyncio.Task | None = None

# estado observável da rotina (em memória, por processo)
_state: dict = {
    "enabled": False,
    "running": False,
    "interval_seconds": 0,
    "started_at": None,   # datetime — quando a rotina subiu
    "last_run_at": None,  # datetime — início da última execução (auto ou manual)
    "last_run_source": None,  # "auto" | "manual"
    "last_result": None,  # dict devolvido por poll_melhor_envio_tracking
    "next_run_at": None,  # datetime — quando a próxima execução automática dispara
    "runs": 0,
}


def _now() -> datetime:
    return datetime.now(UTC)


def note_run(result: dict, *, source: str) -> None:
    """Registra que uma sincronização acabou de rodar (chamado pelo loop e
    também pelo disparo manual do painel)."""
    _state["last_run_at"] = _now()
    _state["last_run_source"] = source
    _state["last_result"] = result
    _state["runs"] += 1


def status() -> dict:
    """Fotografia do estado da rotina, para o painel."""
    now = _now()
    nxt = _state["next_run_at"]
    secs = None
    if _state["enabled"] and nxt is not None:
        secs = max(0, int((nxt - now).total_seconds()))
    last = _state["last_run_at"]
    since = int((now - last).total_seconds()) if last else None
    return {
        "enabled": _state["enabled"],
        "running": _state["running"],
        "interval_seconds": _state["interval_seconds"],
        "started_at": _state["started_at"].isoformat() if _state["started_at"] else None,
        "last_run_at": last.isoformat() if last else None,
        "last_run_source": _state["last_run_source"],
        "seconds_since_last_run": since,
        "next_run_at": nxt.isoformat() if nxt else None,
        "seconds_until_next_run": secs,
        "runs": _state["runs"],
        "last_result": _state["last_result"],
    }


async def _resolve_interval() -> int:
    """Intervalo efetivo (segundos): o valor do menu Frete quando > 0, senão o
    padrão do servidor. Se a leitura da config falhar, MANTÉM o último valor
    conhecido — nunca "salta" de volta para o padrão. Mínimo 120 s."""
    try:
        from app.modules.shipping.service import load_config

        async with SessionLocal() as db:
            cfg = await load_config(db)
        override = int(getattr(cfg, "me_poll_interval_seconds", 0) or 0)
    except Exception:  # noqa: BLE001
        logger.warning(
            "rotina ME: falha ao ler o intervalo da config; mantendo o valor atual",
            exc_info=True,
        )
        last = int(_state.get("interval_seconds") or 0)
        return last if last >= 120 else max(120, settings.me_poll_interval_seconds)
    base = override or settings.me_poll_interval_seconds
    return max(120, base)


async def _tick_once() -> None:
    from app.modules.shipping.service import poll_melhor_envio_tracking

    async with SessionLocal() as db:
        try:
            result = await poll_melhor_envio_tracking(db)
            await db.commit()  # SessionLocal não faz commit no fim do `async with`
        except Exception:
            await db.rollback()
            raise
    note_run(result, source="auto")
    if result.get("updated"):
        logger.info("sincronização Melhor Envio: %s", result)


async def _loop() -> None:
    _state.update(enabled=True, running=True, started_at=_now())
    _state["interval_seconds"] = await _resolve_interval()
    logger.info(
        "rotina de rastreio Melhor Envio ativa (intervalo=%ss)", _state["interval_seconds"]
    )
    # atraso no boot para não competir com a subida
    await asyncio.sleep(min(30, _state["interval_seconds"]))
    while True:
        _state["next_run_at"] = _now()
        try:
            await _tick_once()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - nunca deixa a task morrer
            logger.exception("falha no tick da rotina de rastreio do Melhor Envio")

        # Espera até o próximo disparo, mas relendo o intervalo a cada ~15 s:
        # mudança no menu Frete pega em segundos e o status fica sempre correto.
        # A âncora é o último run (automático OU manual pelo painel).
        while True:
            interval = await _resolve_interval()
            _state["interval_seconds"] = interval
            anchor = _state["last_run_at"] or _now()
            target = anchor + timedelta(seconds=interval)
            _state["next_run_at"] = target
            remaining = (target - _now()).total_seconds()
            if remaining <= 0:
                break
            await asyncio.sleep(min(15.0, remaining))


def start() -> None:
    global _task
    if not settings.me_poll_enabled or settings.api_env == "test":
        _state["enabled"] = False
        return
    if _task and not _task.done():
        return
    _task = asyncio.create_task(_loop(), name="melhor-envio-tracking-poll")


async def stop() -> None:
    global _task
    _state.update(running=False, enabled=False, next_run_at=None)
    if _task and not _task.done():
        _task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _task
    _task = None
