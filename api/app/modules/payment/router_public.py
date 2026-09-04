"""Rotas públicas do módulo `payment`."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.ratelimit import rate_limit
from app.modules.payment import service
from app.modules.payment.schemas import ChargeIn, ChargeOut, PaymentStatusOut

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("/charge", response_model=ChargeOut)
async def charge(
    body: ChargeIn,
    db: DbDep,
    background: BackgroundTasks,
    _rl: Annotated[None, Depends(rate_limit("20/minute", scope="pay-charge"))],
):
    # e-mail de confirmação + fatura em PDF rodam DEPOIS da resposta — o cliente
    # não fica esperando SMTP/PDF pra saber se o cartão foi aprovado.
    payment = await service.create_charge(
        db,
        order_number=body.order_number,
        method=body.method,
        card=body.card.model_dump() if body.card else None,
        background=background,
    )
    return service.charge_out(payment, body.order_number)


@router.get("/status/{order_number}", response_model=PaymentStatusOut)
async def status(order_number: str, db: DbDep):
    return await service.get_status(db, order_number)


@router.get("/methods")
async def methods(db: DbDep) -> dict:
    """Métodos de pagamento habilitados — consumido pelo checkout da loja."""
    cfg = await service.load_config(db)
    return {
        "credit_card": cfg.methods.credit_card,
        "pix": cfg.methods.pix,
        "boleto": cfg.methods.boleto,
        "max_installments": cfg.max_installments,
    }
