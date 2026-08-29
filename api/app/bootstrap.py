"""Descoberta de módulos — usado por `main.py` e por scripts (seed, testes)."""
from __future__ import annotations

import importlib
import logging
import pkgutil

logger = logging.getLogger("bootstrap")

_done = False


def discover_modules() -> None:
    """Importa `app.modules.<x>.module` de cada subpacote (auto-discovery).

    Adicionar um módulo novo não exige editar nenhum arquivo central.
    """
    global _done
    if _done:
        return
    import app.modules as modules_pkg

    for mod in pkgutil.iter_modules(modules_pkg.__path__):
        if not mod.ispkg:
            continue
        try:
            importlib.import_module(f"app.modules.{mod.name}.module")
        except ModuleNotFoundError as exc:
            if exc.name and exc.name.endswith(f"{mod.name}.module"):
                logger.warning("módulo '%s' sem module.py — ignorado", mod.name)
            else:
                raise
    _done = True
