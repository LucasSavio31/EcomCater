"""Fatura do pedido em PDF (fpdf2 — sem browser).

Usada como anexo do e-mail de pagamento confirmado e no download do painel.
Fonte core (Helvetica / latin-1) — cobre acento do português; evitamos
caracteres fora do cp1252 (traço curto, bullets Unicode, emoji).
"""
from __future__ import annotations

from datetime import UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.orders.models import Order, OrderItem
from app.shared.timez import store_tz


def _money(cents: int | None) -> str:
    return f"R$ {(cents or 0) / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _latin1(text: str) -> str:
    return (text or "").encode("latin-1", "replace").decode("latin-1")


async def build_invoice_pdf(db: AsyncSession, order: Order) -> bytes:
    from fpdf import FPDF

    from app.modules.admin.models import StoreSettings
    from app.modules.payment.models import Payment

    store = await db.get(StoreSettings, 1)
    pay = await db.scalar(
        select(Payment).where(Payment.order_id == order.id).order_by(Payment.created_at.desc())
    )
    items: list[OrderItem] = list(order.items)
    addr = order.shipping_address_json or {}
    svc = order.shipping_service_json or {}

    placed = order.placed_at
    if placed and placed.tzinfo is None:
        placed = placed.replace(tzinfo=UTC)
    placed_str = placed.astimezone(store_tz()).strftime("%d/%m/%Y %H:%M") if placed else "-"

    pay_labels = {
        "pix": "Pix", "boleto": "Boleto", "credit_card": "Cartao de credito",
        "card": "Cartao de credito", "debit_card": "Cartao de debito",
    }
    pay_method = pay_labels.get(pay.method, pay.method) if pay else "-"

    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(16, 14, 16)
    pdf.add_page()
    w = pdf.epw  # largura util

    def line(txt: str, *, size: int = 10, style: str = "", h: float = 5.2) -> None:
        pdf.set_font("Helvetica", style, size)
        pdf.multi_cell(w, h, _latin1(txt), new_x="LMARGIN", new_y="NEXT")

    # cabecalho
    line(store.store_name if store and store.store_name else "Loja", size=15, style="B", h=7)
    if store and store.legal_name:
        line(store.legal_name, size=9)
    if store and store.cnpj:
        line(f"CNPJ {store.cnpj}", size=9)
    pdf.ln(2)
    line("FATURA - Documento de Fatura Eletronica", size=12, style="B", h=6.5)
    line(f"Pedido {order.number}   -   {placed_str}", size=10)
    pdf.ln(2)

    # cliente + entrega
    line("Cliente", size=10, style="B")
    line(addr.get("recipient_name") or order.email)
    line(order.email)
    if order.cpf:
        line(f"CPF {order.cpf}")
    pdf.ln(1)
    line("Entrega", size=10, style="B")
    linha = f"{addr.get('street', '')}, {addr.get('number', '')}".strip(", ")
    if addr.get("complement"):
        linha += f" - {addr['complement']}"
    line(linha)
    line(
        f"{addr.get('district', '')} - {addr.get('city', '')}/{(addr.get('state') or '').upper()}"
        f"  CEP {addr.get('zip', '')}"
    )
    if order.shipping_method or svc.get("name"):
        line(f"Frete: {order.shipping_method or svc.get('name')}")
    pdf.ln(3)

    # itens
    c1, c4 = 14, 27
    c2 = w - c1 - c4 - c4
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(c1, 6, "Qtd", border="B")
    pdf.cell(c2, 6, "Descricao", border="B")
    pdf.cell(c4, 6, "Unit.", border="B", align="R")
    pdf.cell(c4, 6, "Total", border="B", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for it in items:
        name = it.name or "Item"
        if it.variant_label:
            name += f" ({it.variant_label})"
        # trunca a descricao pra caber numa linha (fatura enxuta)
        while pdf.get_string_width(_latin1(name)) > c2 - 2 and len(name) > 4:
            name = name[:-2]
        li = (it.unit_price_cents or 0) * it.quantity
        pdf.cell(c1, 5.5, str(it.quantity), border="B")
        pdf.cell(c2, 5.5, _latin1(name), border="B")
        pdf.cell(c4, 5.5, _money(it.unit_price_cents), border="B", align="R")
        pdf.cell(c4, 5.5, _money(li), border="B", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)

    # totais
    def total_row(label: str, value: str, *, bold: bool = False) -> None:
        pdf.set_font("Helvetica", "B" if bold else "", 10 if not bold else 11)
        pdf.cell(w - c4 - c4, 6, _latin1(label), align="R")
        pdf.cell(c4 + c4, 6, _latin1(value), align="R", new_x="LMARGIN", new_y="NEXT")

    total_row("Subtotal", _money(order.items_total_cents))
    if order.discount_cents:
        cup = f" ({order.coupon_code})" if order.coupon_code else ""
        total_row(f"Desconto{cup}", "- " + _money(order.discount_cents))
    total_row("Frete", _money(order.shipping_cents))
    total_row("Total", _money(order.grand_total_cents), bold=True)
    pdf.ln(3)
    line(f"Pagamento: {pay_method}", size=10)
    if svc.get("tracking_code"):
        line(f"Rastreio: {svc['tracking_code']}", size=10)

    pdf.ln(6)
    line(
        "Documento gerado eletronicamente pela loja. Nao substitui nota fiscal.",
        size=8,
    )

    out = pdf.output()
    return bytes(out)
