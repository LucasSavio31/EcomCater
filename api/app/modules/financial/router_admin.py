"""Rotas administrativas do módulo `financial` (menu Faturamento)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin
from app.modules.admin.models import AdminUser
from app.modules.financial import service
from app.shared.timez import parse_day_bound

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]


def _window(date_from: str | None, date_to: str | None) -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    ws = parse_day_bound(date_from, end=False)
    we = parse_day_bound(date_to, end=True)
    if ws is None and we is None:
        return now - timedelta(days=30), now
    if ws is None:
        ws = we - timedelta(days=30)
    if we is None:
        we = now
    return ws, we


@router.get("/summary")
async def summary(
    db: DbDep,
    _: AdminDep,
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
) -> dict:
    """Faturamento bruto/líquido, margem, estorno, cancelamento e total de
    pedidos do período — vindo do livro-caixa (cumulativo, à prova de
    exclusão de pedidos)."""
    ws, we = _window(date_from, date_to)
    data = await service.summary(db, ws, we)
    data["window"] = {"from": ws.isoformat(), "to": we.isoformat()}
    return data


@router.get("/report.pdf")
async def report_pdf(
    db: DbDep,
    _: AdminDep,
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
) -> Response:
    """Relatório de faturamento em PDF do mesmo período do menu -- cabeçalho
    com os dados da loja, resumo, faturamento por forma de pagamento e a
    evolução no período. Gerado na hora (WeasyPrint, sem navegador)."""
    from app.modules.financial.report import build_financial_report_pdf

    ws, we = _window(date_from, date_to)
    pdf = await build_financial_report_pdf(db, ws, we)
    fname = f"faturamento-{ws.date().isoformat()}-a-{we.date().isoformat()}.pdf"
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
