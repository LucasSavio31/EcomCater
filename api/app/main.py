"""Ponto de entrada da API. Descobre e monta todos os módulos."""
from __future__ import annotations

import logging
import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

# StaticFiles usa mimetypes.guess_type; sem isto, .webp sai como
# application/octet-stream (o navegador sniffa, mas o tipo errado atrapalha
# cache/otimização). Registra os formatos de imagem modernos no boot.
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/avif", ".avif")
mimetypes.add_type("image/svg+xml", ".svg")

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
    # agendadores internos (rodam no processo da API, trava de worker único).
    # RUN_SCHEDULERS=0 nos processos que só servem a loja — assim os relatórios
    # e rotinas de fundo não disputam worker/conexão com a navegação.
    schedulers: list = []
    if settings.run_schedulers:
        from app.modules.cart_recovery import scheduler as recovery_scheduler
        from app.modules.shipping import scheduler as me_tracking_scheduler
        from app.modules.system import email_retry as email_retry_scheduler
        from app.modules.system import health_scheduler
        from app.modules.system import scheduler as backup_scheduler

        schedulers = [
            backup_scheduler,
            me_tracking_scheduler,
            health_scheduler,
            recovery_scheduler,
            email_retry_scheduler,
        ]
        for s in schedulers:
            s.start()
    else:
        logger.info("RUN_SCHEDULERS=0 — agendadores internos desligados neste processo")
    try:
        yield
    finally:
        for s in schedulers:
            await s.stop()


def create_app() -> FastAPI:
    # Em prod: schema/UI de docs desligados — expor todas as rotas/modelos
    # publicamente é reconhecimento de graça pra quem for atacar a API.
    app = FastAPI(
        title="E-commerce API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.is_prod else "/docs",
        redoc_url=None if settings.is_prod else "/redoc",
        openapi_url=None if settings.is_prod else "/openapi.json",
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
