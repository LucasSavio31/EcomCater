"""Cria um cliente de teste + 2 pedidos (1 pago, 1 pendente) para inspeção.

Uso:  python -m app.seed.test_order
Login do cliente:  cliente.teste@example.com  /  senha = CPF 37183917835
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

import app.models  # noqa: F401 - registra todos os mappers
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.cart import service as cart_service
from app.modules.customers.models import User
from app.modules.orders import service as order_service
from app.modules.products.models import Product, ProductVariant

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed.test_order")

EMAIL = "cliente.teste@example.com"
CPF = "37183917835"
ADDR = {
    "recipient_name": "Cliente Teste",
    "zip": "01001000",
    "street": "Praça da Sé",
    "number": "100",
    "complement": "Apto 12",
    "district": "Sé",
    "city": "São Paulo",
    "state": "SP",
    "country": "BR",
    "phone": "11999998888",
}


async def _ensure_user(db) -> User:
    u = await db.scalar(select(User).where(User.email == EMAIL))
    if u:
        return u
    u = User(
        full_name="Cliente Teste",
        email=EMAIL,
        password_hash=hash_password(CPF),
        phone=ADDR["phone"],
        cpf=CPF,
        is_active=True,
    )
    db.add(u)
    await db.flush()
    logger.info("cliente de teste criado: %s (senha = CPF %s)", EMAIL, CPF)
    return u


async def _make_order(user_id: str, *, pay: bool) -> str:
    """Sessão própria por pedido — evita reaproveitar carrinho já convertido."""
    async with SessionLocal() as db:
        variant = await db.scalar(
            select(ProductVariant)
            .join(Product, Product.id == ProductVariant.product_id)
            .where(
                ProductVariant.is_active.is_(True),
                ProductVariant.stock_qty > 0,
                Product.status == "active",
            )
            .limit(1)
        )
        if not variant:
            raise RuntimeError("Sem variante em estoque — rode `python -m app.seed.sneaker` antes.")
        user = await db.scalar(select(User).where(User.id == user_id))

        cart = await cart_service.get_or_create(db, token=None, user_id=str(user.id))
        cart = await cart_service.add_item(db, cart, str(variant.id), 1)
        order = await order_service.create_from_cart(
            db,
            cart,
            email=EMAIL,
            cpf=CPF,
            shipping_address=ADDR,
            billing_address=None,
            customer_note="Pedido de teste (seed)",
        )
        await cart_service.clear(db, cart)
        if pay:
            await order_service.finalize_paid(db, order)
        number = order.number
        await db.commit()
        logger.info("pedido %s criado (%s)", number, "PAGO" if pay else "pendente")
        return number


async def run() -> None:
    async with SessionLocal() as db:
        user = await _ensure_user(db)
        await db.commit()
        user_id = str(user.id)
    n1 = await _make_order(user_id, pay=True)
    n2 = await _make_order(user_id, pay=False)
    logger.info("OK — cliente %s | pedidos: %s (pago), %s (pendente)", EMAIL, n1, n2)


if __name__ == "__main__":
    asyncio.run(run())
