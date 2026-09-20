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

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
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


@admin_router.get("/test-connection")
async def test_connection(db: DbDep, _: SuperDep) -> dict:
    """Consulta status do serviço na SEFAZ -- não emite nada, só confirma
    certificado + conectividade antes de emitir a primeira nota de verdade."""
    return await service.test_connection(db)


def _doc_out(doc) -> dict:
    return {
        "id": str(doc.id),
        "order_number": doc.order_number,
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


def _doc_out_full(doc) -> dict:
    """Versão maior de `_doc_out`, pra listagem/detalhe: valor, natureza da
    operação, destinatário e a justificativa do cancelamento (quando houver)."""
    payload = doc.payload_json or {}
    dest = payload.get("destinatario") or {}
    return {
        **_doc_out(doc),
        "total_cents": doc.total_cents,
        "natureza_operacao": payload.get("natureza_operacao"),
        "destinatario_nome": dest.get("nome"),
        "cancel_justificativa": doc.cancel_justificativa,
        "created_at": doc.created_at.isoformat(),
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


@admin_router.get("/orders/{number}/mini-danfe")
async def download_mini_danfe(number: str, db: DbDep, _: EditorDep) -> Response:
    """DANFE Simplificado – Etiqueta (NT 2020.004), 10x15 -- pra imprimir na
    térmica junto com a etiqueta de envio, igual Mercado Livre/Shopee."""
    content, filename = await service.get_mini_danfe(db, number)
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


# --------------------------------------------------------------- lote (seleção múltipla na listagem)


@admin_router.post("/status-map")
async def status_map(body: dict, db: DbDep, _: EditorDep) -> dict:
    """Status da NF-e mais recente de vários pedidos de uma vez -- alimenta
    a coluna "NF-e" na listagem sem um GET por linha."""
    numbers = [str(n) for n in body.get("numbers", []) if n]
    latest = await service.latest_for_order_numbers(db, numbers)
    return {
        "results": [
            _doc_out(latest[number]) if number in latest else {"order_number": number, "status": "none"}
            for number in numbers
        ]
    }


@admin_router.post("/bulk-emit")
async def bulk_emit(body: dict, db: DbDep, admin: EditorDep) -> dict:
    """Emite vários pedidos de uma vez, sem tela de revisão -- usa o
    rascunho automático. Um pedido com problema não impede os outros."""
    numbers = [str(n) for n in body.get("numbers", []) if n]
    results = await service.bulk_emit(db, numbers, admin.id)
    return {"results": results}


@admin_router.get("/export-month")
async def export_month(
    db: DbDep,
    _: EditorDep,
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
) -> Response:
    """.zip com o XML de todas as NF-e autorizadas no mês -- pra mandar pro
    contador. O XML já fica guardado no sistema desde a emissão; isso só
    agrupa por mês."""
    content, filename = await service.export_month_zip(db, year, month)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@admin_router.get("/bulk-danfe")
async def bulk_danfe(
    db: DbDep,
    _: EditorDep,
    numbers: str = Query(..., description="números de pedido separados por vírgula"),
    mini: bool = Query(False, description="DANFE Simplificado – Etiqueta (10x15) em vez do DANFE cheio"),
) -> Response:
    nums = [n.strip() for n in numbers.split(",") if n.strip()]
    pdf, skipped = await service.bulk_danfe_pdf(db, nums, mini=mini)
    filename = "etiquetas-nfe.pdf" if mini else "danfes.pdf"
    headers = {"Content-Disposition": f'inline; filename="{filename}"'}
    if skipped:
        # nomes de pedido não contêm vírgula -- seguro juntar assim
        headers["X-Nfe-Skipped"] = ",".join(skipped)
    return Response(content=pdf, media_type="application/pdf", headers=headers)


# --------------------------------------------------------------- listagem (todas as NF-e)


@admin_router.get("/documents")
async def list_documents(
    db: DbDep,
    _: EditorDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10),
    status: str | None = Query(default=None),
) -> dict:
    if page_size not in (10, 20, 50, 100):
        page_size = 10
    rows, total = await service.list_documents(db, page=page, page_size=page_size, status=status)
    return {"items": [_doc_out_full(r) for r in rows], "total": total, "page": page, "page_size": page_size}


@admin_router.get("/documents/{doc_id}")
async def get_document(doc_id: str, db: DbDep, _: EditorDep) -> dict:
    doc = await service.get_document(db, doc_id)
    return _doc_out_full(doc)


@admin_router.get("/documents/{doc_id}/xml")
async def download_document_xml(doc_id: str, db: DbDep, _: EditorDep) -> Response:
    content, filename = await service.get_document_xml(db, doc_id)
    return Response(
        content=content,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@admin_router.get("/documents/{doc_id}/danfe")
async def download_document_danfe(doc_id: str, db: DbDep, _: EditorDep) -> Response:
    content, filename = await service.get_document_danfe(db, doc_id)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@admin_router.get("/documents/{doc_id}/mini-danfe")
async def download_document_mini_danfe(doc_id: str, db: DbDep, _: EditorDep) -> Response:
    content, filename = await service.get_document_mini_danfe(db, doc_id)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@admin_router.post("/documents/{doc_id}/email")
async def email_document(doc_id: str, body: dict, db: DbDep, _: EditorDep) -> dict:
    doc = await service.get_document(db, doc_id)
    to = str(body.get("to") or "").strip()
    if not to:
        raise ValidationError("Informe o e-mail de destino.")
    await service.send_document_email(db, doc, to, mini=bool(body.get("mini")))
    return {"ok": True}


@admin_router.post("/documents/{doc_id}/cancel")
async def cancel_document(doc_id: str, body: dict, db: DbDep, admin: EditorDep) -> dict:
    doc = await service.get_document(db, doc_id)
    doc = await service.cancel(db, doc, body.get("justificativa", ""), admin.id)
    return _doc_out_full(doc)


@admin_router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, db: DbDep, _: EditorDep) -> dict:
    doc = await service.get_document(db, doc_id)
    await service.delete_document(db, doc)
    return {"ok": True}
