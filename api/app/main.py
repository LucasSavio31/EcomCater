"""Ponto de entrada da API. Descobre e monta todos os módulos."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.bootstrap import discover_modules
from app.core.cache_bust import CacheBust
from app.core.cache_headers import PublicCacheHeaders
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.module_registry import register_all

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # em produção, não sobe com segredos padrão de dev
    settings.assert_prod_secrets()
    # garante o diretório de mídia local
    if settings.storage_backend == "local":
        Path(settings.storage_local_dir).mkdir(parents=True, exist_ok=True)
    # agendador interno de backup (ver app/modules/system/scheduler.py)
    from app.modules.system import scheduler as backup_scheduler

    # rotina de sincronização de rastreio com o Melhor Envio
    from app.modules.shipping import scheduler as me_tracking_scheduler

    # amostragem de saúde dos serviços a cada janela de 15 min
    from app.modules.system import health_scheduler

    backup_scheduler.start()
    me_tracking_scheduler.start()
    health_scheduler.start()
    try:
        yield
    finally:
        await backup_scheduler.stop()
        await me_tracking_scheduler.stop()
        await health_scheduler.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="E-commerce API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Só em dev: libera localhost e qualquer IP de LAN privada (192.168/10/172.16-31)
    # em qualquer porta — necessário para abrir a loja pelo IP da máquina no celular.
    dev_lan_regex = (
        None
        if settings.is_prod
        else (
            r"^http://(localhost|127\.0\.0\.1|"
            r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
            r"192\.168\.\d{1,3}\.\d{1,3}|"
            r"172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(:\d+)?$"
        )
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=dev_lan_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Cache-Control em GET público (catálogo/tema/menus/mídia) — janela curta
    # p/ proxy/navegador/CDN; invalidação real é por tag no Next.
    app.add_middleware(PublicCacheHeaders)
    # Invalida o cache de leitura (Redis) quando o admin salva catálogo/tema.
    app.add_middleware(CacheBust)

    register_error_handlers(app)

    discover_modules()
    register_all(app)

    @app.get("/health", tags=["meta"])
    async def health() -> dict:
        return {"status": "ok", "env": settings.api_env}

    # serve mídia local em dev (em prod o LiteSpeed serve o diretório)
    if settings.storage_backend == "local":
        Path(settings.storage_local_dir).mkdir(parents=True, exist_ok=True)
        app.mount(
            "/media",
            StaticFiles(directory=settings.storage_local_dir),
            name="media",
        )

    return app


app = create_app()
