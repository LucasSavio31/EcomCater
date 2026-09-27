"""Código 2D do pedido na fatura: QR Code que aponta para o pedido na loja.

Sem login → cai na tela de login e, ao entrar, abre o pedido
(a lista de "Meus pedidos" lê `?pedido=` e expande/rola até ele).
"""
from __future__ import annotations

from app.modules.domains.sites import url_for


def order_store_url(number: str, site: str | None = None) -> str:
    """Link do pedido na loja do domínio em que ele foi feito (multi-domínio)."""
    return f"{url_for(site)}/minha-conta/pedidos?pedido={number}"


def order_qr_svg(number: str, site: str | None = None) -> str:
    import segno

    return segno.make(order_store_url(number, site), error="m").svg_inline(scale=4, border=2, dark="#111111")


def order_qr_data_uri(number: str, site: str | None = None) -> str | None:
    try:
        import segno

        return segno.make(order_store_url(number, site), error="m").png_data_uri(
            scale=4, border=2, dark="#111111"
        )
    except Exception:  # noqa: BLE001
        return None
