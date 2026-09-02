"""Rotas públicas do módulo `orders` — checkout e acompanhamento."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_customer_optional
from app.core.ratelimit import rate_limit
from app.modules.cart import service as cart_service
from app.modules.customers.models import User
from app.modules.orders import service
from app.modules.orders.schemas import CheckoutIn, OrderOut

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
UserDep = Annotated[User | None, Depends(get_current_customer_optional)]


@router.post("/checkout", response_model=None, status_code=status.HTTP_201_CREATED)
async def checkout(
    body: CheckoutIn,
    request: Request,
    response: Response,
    db: DbDep,
    user: UserDep,
    _rl: Annotated[None, Depends(rate_limit("20/minute", scope="checkout"))],
    cart_token: Annotated[str | None, Cookie(alias="cart_token")] = None,
):
    cart = await cart_service.get_or_create(
        db, token=cart_token, user_id=str(user.id) if user else None
    )
    if body.shipping_service_id and cart.shipping_zip:
        cart = await cart_service.select_shipping(db, cart, body.shipping_service_id)

    # atribuição de marketing p/ Meta CAPI + Google Enhanced Conversions
    fwd = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    marketing = {
        "fbp": body.fbp,
        "fbc": body.fbc,
        "ga_client_id": body.ga_client_id,
        "landing_url": body.landing_url,
        "client_ip": fwd or (request.client.host if request.client else None),
        "client_user_agent": request.headers.get("user-agent"),
    }
    marketing = {k: v for k, v in marketing.items() if v}

    order = await service.create_from_cart(
        db,
        cart,
        email=body.email,
        cpf=body.cpf,
        shipping_address=body.shipping_address.model_dump(),
        billing_address=body.billing_address.model_dump() if body.billing_address else None,
        customer_note=body.customer_note,
        idempotency_key=body.idempotency_key,
        marketing=marketing or None,
    )

    # comprador vira usuário do sistema e já sai logado (para ir a "minhas compras")
    from app.modules.customers.service import (
        ensure_user_for_checkout,
        sync_default_address,
    )

    addr = body.shipping_address.model_dump()
    auth: dict | None = None
    buyer = user
    if not user:
        buyer, pair = await ensure_user_for_checkout(
            db,
            email=body.email,
            cpf=body.cpf,
            full_name=addr.get("recipient_name") or "",
            phone=addr.get("phone"),
        )
        order.user_id = buyer.id
        auth = pair
    # o endereço da última compra vira o endereço padrão do cliente
    if buyer is not None:
        if not buyer.phone and addr.get("phone"):
            buyer.phone = addr["phone"]
        await sync_default_address(db, buyer, addr)
    await db.flush()

    await cart_service.clear(db, cart)
    full = await service._load(db, order.id)

    # commit ANTES de emitir: os subscribers de `order.created` (e-mail ao
    # cliente/lojista, marcar carrinho recuperado, virar lead) abrem a própria
    # sessão e só enxergam o pedido depois de gravado.
    await db.commit()
    from app.core.events import emit

    await emit("order.created", {"order_id": str(order.id), "number": order.number})

    return {**service.to_out(full), "auth": auth}


@router.get("")
async def my_orders(db: DbDep, user: UserDep):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.modules.orders.models import Order

    if not user:
        from app.core.errors import AuthError

        raise AuthError("Faça login para ver seus pedidos.")
    orders = list(
        await db.scalars(
            select(Order)
            .where(Order.user_id == user.id)
            .options(selectinload(Order.items), selectinload(Order.events))
            .order_by(Order.placed_at.desc().nullslast())
        )
    )
    pay_by_order = await service.payments_for_orders(db, [o.id for o in orders])
    return [
        {**service.to_out(o), "payment": pay_by_order.get(str(o.id))} for o in orders
    ]


@router.get("/{number}/pulse")
async def order_pulse(
    number: str,
    db: DbDep,
    user: UserDep,
    email: str | None = Query(None),
):
    """Batimento leve do pedido para atualização quase em tempo real na conta
    do cliente, sem baixar o pedido inteiro a cada poll."""
    if user:
        try:
            order = await service.get_by_number(db, number)
            if order.user_id and str(order.user_id) == str(user.id):
                return await service.order_pulse(db, number)
        except Exception:  # noqa: BLE001
            pass
    # convidado/não-dono: só com e-mail correspondente (evita enumeração)
    order = await service.get_by_number(db, number, email=email, require_email=True)
    return await service.order_pulse(db, order.number, email=order.email)


@router.get("/{number}", response_model=OrderOut)
async def get_order(
    number: str,
    db: DbDep,
    user: UserDep,
    email: str | None = Query(None),
):
    if user:
        order = await service.get_by_number(db, number)
        if order.user_id and str(order.user_id) == str(user.id):
            return {**service.to_out(order), "payment": await service.payment_for_order(db, order.id)}
    # convidado/não-dono: exige e-mail correspondente (impede enumeração por número)
    order = await service.get_by_number(db, number, email=email, require_email=True)
    return {**service.to_out(order), "payment": await service.payment_for_order(db, order.id)}
