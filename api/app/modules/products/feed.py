"""Feed de produtos no formato Google Merchant Center (RSS 2.0 + namespace
`g:`) -- https://support.google.com/merchants/answer/7052112.

Rota pública, montada ao vivo a partir do catálogo (o Merchant Center busca
esse link sozinho, periodicamente -- não precisa de cache/job próprio aqui).
Um item por VARIANTE ativa (não por produto): pra roupa/calçado, cada
numeração tem disponibilidade própria, e é assim que a Google recomenda
listar -- `g:item_group_id` agrupa as variantes do mesmo produto na
Shopping ads.
"""
from __future__ import annotations

import re
from xml.etree.ElementTree import Element, SubElement, register_namespace, tostring

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.modules.products.models import Product, ProductVariant
from app.modules.products.service import variant_price
from app.shared.storage import storage

_G_NS = "http://base.google.com/ns/1.0"
register_namespace("g", _G_NS)

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]+")


def _g(tag: str) -> str:
    return f"{{{_G_NS}}}{tag}"


def _strip_html(html: str | None) -> str:
    if not html:
        return ""
    txt = html.replace("</p>", "\n").replace("<br>", "\n").replace("<br/>", "\n")
    txt = _TAG_RE.sub("", txt)
    txt = _WS_RE.sub(" ", txt)
    lines = [ln.strip() for ln in txt.splitlines()]
    return "\n".join(ln for ln in lines if ln).strip()


def _variant_in_stock(v: ProductVariant) -> bool:
    return v.is_active and (v.stock_qty is None or v.stock_qty > 0)


async def build_feed_xml(db: AsyncSession) -> bytes:
    from app.modules.admin.models import StoreSettings

    store = await db.get(StoreSettings, 1)
    store_name = (store.store_name if store else None) or "Loja"

    products = list(
        await db.scalars(
            select(Product)
            .where(Product.status == "active")
            .options(
                selectinload(Product.variants).selectinload(ProductVariant.option_values),
                selectinload(Product.images),
            )
            .order_by(Product.created_at)
        )
    )

    rss = Element("rss", attrib={"version": "2.0"})
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = store_name
    SubElement(channel, "link").text = settings.site_url
    SubElement(channel, "description").text = f"Feed de produtos — {store_name}"

    for product in products:
        images = sorted(product.images, key=lambda i: (not i.is_primary, i.position))
        image_url = storage.url(images[0].zoom_key) if images else None
        if not image_url:
            continue  # Merchant Center recusa item sem imagem -- pula o produto

        link = f"{settings.site_url}/produto/{product.slug}"
        description = _strip_html(product.description) or (product.short_description or product.name)

        variants = [v for v in product.variants if v.is_active]
        # sem variação cadastrada (produto simples) -> 1 item só, usando o próprio produto
        entries: list[ProductVariant | None] = variants or [None]

        for variant in entries:
            item = SubElement(channel, "item")
            item_id = str(variant.id) if variant else str(product.id)
            SubElement(item, _g("id")).text = item_id
            SubElement(item, _g("item_group_id")).text = str(product.id)

            labels = [ov.value for ov in variant.option_values] if variant else []
            title = f"{product.name} - {', '.join(labels)}" if labels else product.name
            SubElement(item, "title").text = title[:150]
            SubElement(item, "description").text = description[:5000]
            SubElement(item, "link").text = link
            SubElement(item, _g("image_link")).text = image_url

            price_cents = variant_price(product, variant) if variant else product.price_cents
            in_stock = _variant_in_stock(variant) if variant else True
            SubElement(item, _g("availability")).text = "in stock" if in_stock else "out of stock"
            SubElement(item, _g("price")).text = f"{price_cents / 100:.2f} BRL"
            SubElement(item, _g("condition")).text = "new"
            SubElement(item, _g("brand")).text = product.brand or store_name

            barcode = variant.barcode if variant else None
            if barcode:
                SubElement(item, _g("gtin")).text = barcode
            else:
                mpn = (variant.sku if variant else product.sku_root) or item_id
                SubElement(item, _g("mpn")).text = mpn
                SubElement(item, _g("identifier_exists")).text = "no"

    return tostring(rss, encoding="utf-8", xml_declaration=True)
