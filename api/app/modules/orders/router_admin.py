"""Rotas administrativas do módulo `orders`."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query
from fastapi import status as http_status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import (
    get_current_admin,
    get_current_admin_downloadable,
    require_role,
)
from app.modules.admin.models import AdminUser
from app.modules.orders import service
from app.modules.orders.models import Order
from app.modules.orders.schemas import BulkStatusIn, NoteIn, OrderOut, StatusChangeIn
from app.modules.payment.models import Payment

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]
EditorDep = Annotated[AdminUser, Depends(require_role("admin", "staff"))]


@router.get("")
async def list_orders(
    db: DbDep,
    _: AdminDep,
    status: str | None = None,
    payment_status: str | None = None,
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    bucket: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> dict:
    return await service.admin_list(
        db,
        status=status,
        payment_status=payment_status,
        q=q,
        date_from=date_from,
        date_to=date_to,
        bucket=bucket,
        page=page,
        page_size=page_size,
    )


@router.post("/bulk")
async def orders_bulk(db: DbDep, _: AdminDep, numbers: list[str] = Body(..., embed=True)) -> list[dict]:
    """Pedidos completos por número — usado pelas telas de PDF / etiquetas."""
    return await service.admin_bulk(db, numbers)


async def _payment_out(db: AsyncSession, order: Order) -> dict | None:
    p = await db.scalar(
        select(Payment).where(Payment.order_id == order.id).order_by(Payment.created_at.desc())
    )
    if not p:
        return None
    return {
        "provider": p.provider,
        "method": p.method,
        "status": p.status,
        "amount_cents": p.amount_cents,
        "installments": p.installments,
        "provider_charge_id": p.provider_charge_id,
        "paid_at": p.paid_at.isoformat() if p.paid_at else None,
        "boleto_url": p.boleto_url,
        "pix_qr_code": p.pix_qr_code,
    }


@router.get("/{number}/pulse")
async def order_pulse(number: str, db: DbDep, _: AdminDep) -> dict:
    return await service.order_pulse(db, number)


def _order_code_data_uri(number: str) -> str:
    """Data Matrix (SVG data URI) com o número do pedido — código 2D da Fatura.
    Embutido direto na resposta para não depender de outra requisição
    autenticada na hora de imprimir."""
    import base64

    from ppf.datamatrix import DataMatrix

    svg = DataMatrix(number).svg()
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


@router.get("/{number}/qr.svg")
async def order_qr(
    number: str,
    db: DbDep,
    _: Annotated[AdminUser, Depends(get_current_admin_downloadable)],
) -> Response:
    """Código 2D (Data Matrix, SVG) com o número do pedido — uso avulso."""
    from ppf.datamatrix import DataMatrix

    order = await service.get_by_number(db, number)  # 404 se não existe
    return Response(
        content=DataMatrix(order.number).svg(),
        media_type="image/svg+xml",
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.get("/{number}")
async def get_order(number: str, db: DbDep, _: AdminDep) -> dict:
    order = await service.get_by_number(db, number)
    out = {**service.to_out(order), "payment": await _payment_out(db, order)}
    out["qr_data_uri"] = _order_code_data_uri(order.number)
    return await service.attach_variation_options(db, out)


@router.patch("/{number}")
async def edit_order(number: str, body: dict, db: DbDep, _: EditorDep) -> dict:
    order = await service.edit_order(db, number, body)
    out = {**service.to_out(order), "payment": await _payment_out(db, order)}
    return await service.attach_variation_options(db, out)


@router.delete("/{number}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_order(
    number: str,
    db: DbDep,
    actor: Annotated[AdminUser, Depends(require_role("super_admin"))],
    confirm: bool = Query(default=False),
) -> None:
    """Exclusão de pedido: última instância, só super admin, com confirm=true e
    apenas para pedidos já cancelados. Pedido ativo NUNCA é apagado — cancele."""
    from app.core.guard import require_confirmation

    require_confirmation(confirm, what="excluir um pedido")
    order = await service.get_by_number(db, number)
    if order.status not in ("canceled", "refunded"):
        from app.core.errors import ConflictError

        raise ConflictError(
            "Só é possível excluir um pedido já cancelado/estornado. "
            "Cancele o pedido primeiro (o estoque é devolvido) — os dados ficam preservados."
        )
    await service.delete_order(db, number)


@router.post("/{number}/status", response_model=OrderOut)
async def change_status(
    number: str, body: StatusChangeIn, db: DbDep, admin: EditorDep
) -> dict:
    order = await service.get_by_number(db, number)
    order = await service.transition(
        db, order, body.status, actor_type="admin", actor_id=str(admin.id), message=body.message
    )
    return service.to_out(await service._load(db, order.id))


def _pdf_response(pdf: bytes, filename: str) -> Response:
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/melhor-envio/labels")
async def melhor_envio_labels(
    db: DbDep,
    _: Annotated[AdminUser, Depends(get_current_admin_downloadable)],
    numbers: str = Query(..., description="números de pedido separados por vírgula"),
) -> Response:
    """PDF com as etiquetas de todos os pedidos selecionados (baixa no painel)."""
    from app.modules.shipping import service as shipping

    nums = [n.strip() for n in numbers.split(",") if n.strip()]
    pdf = await shipping.melhor_envio_labels_pdf(db, nums)
    return _pdf_response(pdf, "etiquetas-melhor-envio.pdf")


@router.get("/{number}/melhor-envio/label")
async def melhor_envio_label(
    number: str,
    db: DbDep,
    _: Annotated[AdminUser, Depends(get_current_admin_downloadable)],
) -> Response:
    """PDF da etiqueta do pedido (baixa direto no painel da loja)."""
    from app.modules.shipping import service as shipping

    pdf = await shipping.melhor_envio_labels_pdf(db, [number])
    return _pdf_response(pdf, f"etiqueta-{number}.pdf")


@router.post("/bulk-status")
async def bulk_status(body: BulkStatusIn, db: DbDep, admin: EditorDep) -> dict:
    """Muda o status de vários pedidos de uma vez. Devolve o resultado por pedido."""
    results: list[dict] = []
    for number in body.numbers:
        try:
            order = await service.get_by_number(db, number)
            await service.transition(
                db, order, body.status, actor_type="admin", actor_id=str(admin.id),
                message=body.message,
            )
            results.append({"number": number, "ok": True})
        except Exception as exc:  # noqa: BLE001
            results.append({"number": number, "ok": False, "message": str(exc)})
    return {"results": results}


@router.post("/{number}/notes", response_model=OrderOut)
async def add_note(number: str, body: NoteIn, db: DbDep, admin: EditorDep) -> dict:
    order = await service.get_by_number(db, number)
    await service.add_note(db, order, body.message, str(admin.id))
    return service.to_out(await service._load(db, order.id))
