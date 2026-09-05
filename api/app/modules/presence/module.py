"""Módulo `presence` — "visitantes ao vivo" no dashboard do admin.

Cada página pública manda um heartbeat periódico (`POST /heartbeat`) com o
caminho atual; a presença fica em Redis com TTL curto (é só "quem está na
loja agora" — sem histórico). O admin lê tudo em `GET /live` pro mapa + lista
+ top 10 estados do dashboard.

Desligável nas Configurações → Módulos (começa desligado: é uma feature nova
de rastreamento por IP, precisa ser ativada conscientemente pelo lojista).
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin
from app.core.module_registry import ModuleSpec, register
from app.core.ratelimit import rate_limit
from app.modules.admin.models import AdminUser
from app.modules.presence import service

public_router = APIRouter()
admin_router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]

COOKIE = "visitor_id"
COOKIE_MAX_AGE = 180 * 86400


class HeartbeatIn(BaseModel):
    path: str = "/"


@public_router.post("/heartbeat")
async def heartbeat(
    body: HeartbeatIn,
    request: Request,
    response: Response,
    _rl: Annotated[None, Depends(rate_limit("10/minute", scope="presence"))],
    visitor_id: Annotated[str | None, Cookie(alias=COOKIE)] = None,
) -> dict:
    vid = visitor_id or uuid.uuid4().hex
    if not visitor_id:
        response.set_cookie(
            COOKIE, vid, max_age=COOKIE_MAX_AGE, httponly=True, samesite="lax", path="/"
        )
    ip = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip() or (
        request.client.host if request.client else None
    )
    await service.record(vid, ip, (body.path or "/")[:200])
    return {"ok": True}


@admin_router.get("/live")
async def live(db: DbDep, _: AdminDep) -> dict:
    return await service.list_active(db)


spec = register(
    ModuleSpec(
        slug="presence",
        label="Visitantes ao vivo",
        kind="feature",
        toggleable=True,
        default_enabled=False,
        public_router=public_router,
        admin_router=admin_router,
        tags=["presence"],
    )
)
