"""Rotas administrativas do módulo `shipping`: configuração + teste de cotação."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_admin, require_role
from app.modules.admin.models import AdminUser
from app.modules.shipping import service
from app.modules.shipping.providers.base import Package
from app.modules.shipping.schemas import ShippingConfigIn

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]
AdminRoleDep = Annotated[AdminUser, Depends(require_role("admin"))]


def _config_out(cfg) -> dict:
    base = settings.public_api_url.rstrip("/")
    webhook_url = f"{base}/api/webhooks/shipping/melhor-envio"
    if cfg.webhook_token:
        webhook_url += f"?token={cfg.webhook_token}"
    return {
        "active_provider": cfg.active_provider,
        "origin_zip": cfg.origin_zip,
        "melhor_envio_sandbox": cfg.melhor_envio_sandbox,
        "sender_cpf": cfg.sender_cpf,
        "label_format": cfg.label_format,
        "print_declaration": cfg.print_declaration,
        "me_poll_interval_seconds": getattr(cfg, "me_poll_interval_seconds", 0),
        "has_token": bool(cfg.melhor_envio_token or settings.melhor_envio_token),
        "token_from_env": bool(settings.melhor_envio_token) and not cfg.melhor_envio_token,
        "token_expires_at": cfg.melhor_envio_token_expires_at or None,
        "melhor_envio_client_id": cfg.melhor_envio_client_id,
        "has_client_secret": bool(cfg.melhor_envio_client_secret),
        "oauth_redirect_uri": service.melhor_envio_redirect_uri(),
        "default_package": cfg.default_package.model_dump(),
        "allowed_services": cfg.allowed_services,
        "free_shipping_services": cfg.free_shipping_services,
        "free_shipping_all": getattr(cfg, "free_shipping_all", False),
        "free_shipping_min_cents": getattr(cfg, "free_shipping_min_cents", None),
        # URL que o lojista cadastra no painel do Melhor Envio (inclui o token)
        "webhook_url": webhook_url,
    }


@router.get("/config")
async def get_config(db: DbDep, _: AdminDep) -> dict:
    return _config_out(await service.load_config(db))


@router.put("/config")
async def update_config(body: ShippingConfigIn, db: DbDep, _: AdminRoleDep) -> dict:
    patch = body.model_dump(exclude_unset=True)
    # intervalo da rotina do ME: 0 = padrão do servidor; qualquer valor entre 1 e
    # 119 é elevado para o mínimo de 120 s.
    iv = patch.get("me_poll_interval_seconds")
    if iv is not None and 0 < int(iv) < 120:
        patch["me_poll_interval_seconds"] = 120
    cfg = await service.save_config(db, patch)
    return _config_out(cfg)


@router.get("/melhor-envio/authorize")
async def melhor_envio_authorize(db: DbDep, _: AdminRoleDep) -> dict:
    """Devolve a URL de autorização OAuth do Melhor Envio (o front redireciona)."""
    return {"url": await service.melhor_envio_authorize_url(db)}


@router.post("/melhor-envio/disconnect")
async def melhor_envio_disconnect(db: DbDep, _: AdminRoleDep) -> dict:
    await service.save_config(
        db,
        {
            "melhor_envio_token": "",
            "melhor_envio_refresh_token": "",
            "melhor_envio_token_expires_at": "",
            "melhor_envio_oauth_state": "",
            "melhor_envio_oauth_state_at": "",
        },
    )
    return {"ok": True}


@router.post("/test-quote")
async def test_quote(
    db: DbDep,
    _: AdminDep,
    dest_zip: str = Query(min_length=8, max_length=9),
) -> dict:
    rates = await service.quote(
        db,
        dest_zip="".join(ch for ch in dest_zip if ch.isdigit()),
        packages=[Package(weight_grams=500, length_mm=200, width_mm=150, height_mm=100, insurance_cents=10000)],
    )
    return {"rates": rates}


@router.post("/melhor-envio/send")
async def send_to_melhor_envio(
    db: DbDep,
    _: AdminRoleDep,
    order_numbers: list[str] = Body(..., embed=True),
    buy: bool = Body(True, embed=True),
) -> dict:
    """Gera a etiqueta no Melhor Envio: carrinho → compra (saldo) → gerar → PDF.

    `buy=false` para no carrinho e você finaliza no painel do ME.
    Salva no pedido: id do envio, protocolo, rastreio e link do PDF.
    """
    return await service.send_orders_to_melhor_envio(db, order_numbers, buy=buy)


@router.post("/melhor-envio/sync-tracking")
async def sync_melhor_envio_tracking(db: DbDep, _: AdminRoleDep) -> dict:
    """Força agora a sincronização de rastreio/status com o Melhor Envio
    (a mesma rotina que roda sozinha de tempos em tempos)."""
    from app.modules.shipping import scheduler

    result = await service.poll_melhor_envio_tracking(db)
    scheduler.note_run(result, source="manual")
    return result


@router.get("/melhor-envio/sync-status")
async def melhor_envio_sync_status(_: AdminDep) -> dict:
    """Estado da rotina automática de sincronização de rastreio: se está ativa,
    o intervalo, quando rodou pela última vez e quanto falta para a próxima."""
    from app.modules.shipping import scheduler

    return scheduler.status()
