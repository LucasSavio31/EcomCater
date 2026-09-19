"""Rotas administrativas do módulo `nfe`.

Config/certificado ficam restritos a `super_admin` (mesmo critério de
`domains` — é a chave privada do e-CNPJ da empresa, dá pra assinar
documentos fiscais reais). As ações por pedido (rascunho/emitir/baixar/
cancelar) usam `admin`/`staff`, o mesmo nível das outras ações de pedido
(`orders/router_admin.py:EditorDep`) — é operação do dia a dia, não config
sensível.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_role
from app.core.errors import NotFoundError, ValidationError
from app.modules.admin.models import AdminUser
from app.modules.nfe import service
from app.modules.orders.service import get_by_number

admin_router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
SuperDep = Annotated[AdminUser, Depends(require_role("super_admin"))]
EditorDep = Annotated[AdminUser, Depends(require_role("admin", "staff"))]


def _config_out(cfg) -> dict:
    d = cfg.model_dump()
    d["certificado_senha"] = "•••• configurado" if cfg.certificado_senha else ""
    d["certificado_configurado"] = bool(cfg.certificado_storage_key)
    return d


@admin_router.get("/config")
async def get_config(db: DbDep, _: SuperDep) -> dict:
    return _config_out(await service.load_config(db))


@admin_router.put("/config")
async def update_config(body: dict, db: DbDep, _: SuperDep) -> dict:
    body.pop("certificado_senha", None)  # senha só muda via /config/certificate
    body.pop("certificado_configurado", None)
    cfg = await service.save_config(db, body)
    return _config_out(cfg)


@admin_router.post("/config/certificate")
async def upload_certificate(
    db: DbDep,
    _: SuperDep,
    file: Annotated[UploadFile, File()],
    senha: Annotated[str, Form()],
) -> dict:
    pfx_bytes = await file.read()
    cfg = await service.upload_certificate(db, pfx_bytes, senha)
    return _config_out(cfg)


def _doc_out(doc) -> dict:
    return {
        "id": str(doc.id),
        "status": doc.status,
        "status_message": doc.status_message,
        "ambiente": doc.ambiente,
        "numero": doc.numero,
        "serie": doc.serie,
        "chave_acesso": doc.chave_acesso,
        "protocolo_autorizacao": doc.protocolo_autorizacao,
        "has_xml": bool(doc.xml_key),
        "has_danfe": bool(doc.danfe_key),
        "requested_at": doc.requested_at.isoformat() if doc.requested_at else None,
        "authorized_at": doc.authorized_at.isoformat() if doc.authorized_at else None,
        "canceled_at": doc.canceled_at.isoformat() if doc.canceled_at else None,
    }


@admin_router.get("/orders/{number}/draft")
async def get_draft(number: str, db: DbDep, _: EditorDep) -> dict:
    order = await get_by_number(db, number)
    if not order:
        raise NotFoundError("Pedido não encontrado.")
    return await service.build_draft(db, order)


@admin_router.get("/orders/{number}")
async def get_status(number: str, db: DbDep, _: EditorDep) -> dict:
    order = await get_by_number(db, number)
    if not order:
        raise NotFoundError("Pedido não encontrado.")
    doc = await service.latest_for_order(db, order.id)
    return _doc_out(doc) if doc else {"status": "none"}


@admin_router.post("/orders/{number}")
async def emit(number: str, payload: dict, db: DbDep, admin: EditorDep) -> dict:
    order = await get_by_number(db, number)
    if not order:
        raise NotFoundError("Pedido não encontrado.")
    doc = await service.request_emission(db, order, payload, admin.id)
    return _doc_out(doc)


@admin_router.get("/orders/{number}/xml")
async def download_xml(number: str, db: DbDep, _: EditorDep) -> Response:
    content, filename = await service.get_xml(db, number)
    return Response(
        content=content,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@admin_router.get("/orders/{number}/danfe")
async def download_danfe(number: str, db: DbDep, _: EditorDep) -> Response:
    content, filename = await service.get_danfe(db, number)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@admin_router.post("/orders/{number}/cancel")
async def cancel(number: str, body: dict, db: DbDep, admin: EditorDep) -> dict:
    order = await get_by_number(db, number)
    if not order:
        raise NotFoundError("Pedido não encontrado.")
    doc = await service.latest_for_order(db, order.id)
    if not doc:
        raise ValidationError("Nenhuma NF-e emitida pra este pedido.")
    doc = await service.cancel(db, doc, body.get("justificativa", ""), admin.id)
    return _doc_out(doc)
