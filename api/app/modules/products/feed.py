"""Feed de produtos no formato Google Merchant Center (RSS 2.0 + namespace
`g:`) -- https://support.google.com/merchants/answer/7052112.

Rota pública, montada ao vivo a partir do catálogo (o Merchant Center busca
esse link sozinho, periodicamente -- não precisa de cache/job próprio aqui).
Um item por VARIANTE ativa (não por produto): pra roupa/calçado, cada
numeração tem disponibilidade própria, e é assim que a Google recomenda
listar -- `g:item_group_id` agrupa as variantes do mesmo produto na
Shopping ads.

Vestuário/calçado exige também cor, tamanho, gênero e faixa etária
(`g:color`, `g:size`, `g:gender`, `g:age_group`) -- sem eles o Merchant
Center limita a visibilidade. Não há campo próprio pra gênero/idade: sai do
caminho das categorias do produto ("masculino/botas", "infantil/...").

Cuidados de política (evitar reprovação/suspensão):
- preço = o preço real de venda; NUNCA manda `g:sale_price` a partir do
  "de" (compare_at) -- desconto de referência sem histórico real conta como
  preço enganoso;
- sem GTIN -> só `identifier_exists=no` (sem inventar MPN com o SKU interno);
- título sem CAIXA ALTA (capitalização excessiva é motivo de reprovação).
"""
from __future__ import annotations

import re
import uuid
from xml.etree.ElementTree import Element, SubElement, register_namespace, tostring

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.modules.categories.models import Category
from app.modules.products.models import (
    Product,
    ProductCategory,
    ProductVariant,
    VariantOptionValue,
)
from app.modules.products.service import variant_price
from app.shared.storage import storage

_G_NS = "http://base.google.com/ns/1.0"
register_namespace("g", _G_NS)

# Taxonomia Google: "Vestuário e acessórios > Calçados"
_GPC_SHOES = "187"
_SHOE_WORDS = {
    "bota", "botas", "coturno", "coturnos", "tenis", "tênis", "sapato", "sapatos",
    "sapatenis", "sapatênis", "sandalia", "sandália", "sandalias", "sandálias",
    "chinelo", "chinelos", "mocassim", "mocassins", "calcado", "calçado",
    "calcados", "calçados", "sapatilha", "sapatilhas", "botina", "botinas",
}
_FEMININE_NOUNS = {"bota", "botina", "sandalia", "sandália", "sapatilha", "rasteira"}
_LOWER_WORDS = {"de", "da", "do", "das", "dos", "e", "com", "em", "para"}
_ACCENT_FIX = {"tenis": "Tênis", "sapatenis": "Sapatênis"}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]+")
_BLOCK_END_RE = re.compile(r"</(p|li|div|h[1-6]|tr)>|<br\s*/?>", re.IGNORECASE)
_DESC_COLOR_RE = re.compile(r"\bCor:\s*([^<\n]+)", re.IGNORECASE)


def _g(tag: str) -> str:
    return f"{{{_G_NS}}}{tag}"


def _strip_html(html: str | None) -> str:
    if not html:
        return ""
    txt = _BLOCK_END_RE.sub("\n", html)
    txt = _TAG_RE.sub("", txt)
    txt = _WS_RE.sub(" ", txt)
    lines = [ln.strip() for ln in txt.splitlines()]
    return "\n".join(ln for ln in lines if ln).strip()


def _nice(text: str) -> str:
    """'BOTA COTURNO 2019 LATEGO CASTANHO' -> 'Bota Coturno 2019 Latego Castanho'."""
    out = []
    for i, word in enumerate(text.split()):
        low = word.lower()
        if low in _ACCENT_FIX:
            out.append(_ACCENT_FIX[low])
        elif i > 0 and low in _LOWER_WORDS:
            out.append(low)
        else:
            out.append("-".join(p[:1].upper() + p[1:] for p in low.split("-")))
    return " ".join(out)


def _variant_in_stock(v: ProductVariant) -> bool:
    return v.is_active and (v.stock_qty is None or v.stock_qty > 0)


def _variant_axes(v: ProductVariant | None) -> tuple[str | None, str | None]:
    """(cor, tamanho) da variação, pelo tipo de cada eixo de opção."""
    color = size = None
    for ov in (v.option_values if v else []):
        ot = ov.option_type
        name = (ot.name or "").lower()
        if ot.is_color or "cor" in name:
            color = color or ov.value
        elif ot.is_size or "num" in name or "tam" in name:
            size = size or ov.value
    return color, size


def _segments(paths: list[str]) -> set[str]:
    return {seg for p in paths for seg in p.lower().split("/")}


def _gender(paths: list[str]) -> str:
    segs = _segments(paths)
    fem = bool(segs & {"feminino", "feminina", "mulher"})
    masc = bool(segs & {"masculino", "masculina", "homem"})
    if fem and not masc:
        return "female"
    if masc and not fem:
        return "male"
    return "unisex"


def _age_group(paths: list[str]) -> str:
    segs = _segments(paths)
    if segs & {"bebe", "bebes"}:
        return "infant"
    if segs & {"infantil", "infantis", "kids", "crianca", "criancas"}:
        return "kids"
    return "adult"


def _gender_word(name: str, gender: str) -> str | None:
    """'Masculina'/'Masculino'... pra reforçar o título -- None se unissex ou se
    o nome já diz o gênero."""
    if gender == "unisex":
        return None
    low = name.lower()
    if any(w in low for w in ("mascul", "femin")):
        return None
    first = low.split()[0] if low.split() else ""
    fem_noun = first in _FEMININE_NOUNS
    if gender == "male":
        return "Masculina" if fem_noun else "Masculino"
    return "Feminina" if fem_noun else "Feminino"


def _is_shoe(name: str, paths: list[str]) -> bool:
    words = {w.lower() for w in name.split()}
    return bool((words | _segments(paths)) & _SHOE_WORDS)


async def build_feed_xml(db: AsyncSession) -> bytes:
    from app.modules.admin.models import StoreSettings

    store = await db.get(StoreSettings, 1)
    store_name = (store.store_name if store else None) or "Loja"

    products = list(
        await db.scalars(
            select(Product)
            .where(Product.status == "active")
            .options(
                selectinload(Product.variants)
                .selectinload(ProductVariant.option_values)
                .selectinload(VariantOptionValue.option_type),
                selectinload(Product.images),
            )
            .order_by(Product.created_at)
        )
    )

    cats = {c.id: c for c in await db.scalars(select(Category))}
    extra_cats: dict[uuid.UUID, list[uuid.UUID]] = {}
    for pid, cid in (await db.execute(select(ProductCategory.product_id, ProductCategory.category_id))).all():
        extra_cats.setdefault(pid, []).append(cid)

    def _name_path(cid: uuid.UUID | None) -> str | None:
        names, seen = [], set()
        while cid and cid in cats and cid not in seen:
            seen.add(cid)
            names.append(cats[cid].name)
            cid = cats[cid].parent_id
        return " > ".join(reversed(names)) or None

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
        extra_images = [storage.url(i.zoom_key) for i in images[1:11]]

        link = f"{settings.site_url}/produto/{product.slug}"
        description = _strip_html(product.description) or (product.short_description or product.name)

        cat_ids = [product.category_id, *extra_cats.get(product.id, [])]
        paths = [cats[c].path for c in cat_ids if c in cats and cats[c].path]
        gender, age_group = _gender(paths), _age_group(paths)
        product_type = _name_path(product.category_id)

        base_title = _nice(product.name)
        gender_word = _gender_word(product.name, gender)
        if gender_word:
            base_title = f"{base_title} {gender_word}"

        desc_color = _DESC_COLOR_RE.search(product.description or "")

        variants = [v for v in product.variants if v.is_active]
        # sem variação cadastrada (produto simples) -> 1 item só, usando o próprio produto
        entries: list[ProductVariant | None] = variants or [None]

        for variant in entries:
            item = SubElement(channel, "item")
            item_id = str(variant.id) if variant else str(product.id)
            SubElement(item, _g("id")).text = item_id
            SubElement(item, _g("item_group_id")).text = str(product.id)

            labels = [ov.value for ov in variant.option_values] if variant else []
            title = f"{base_title} - {', '.join(labels)}" if labels else base_title
            SubElement(item, "title").text = title[:150]
            SubElement(item, "description").text = description[:5000]
            SubElement(item, "link").text = link
            SubElement(item, _g("image_link")).text = image_url
            for extra in extra_images:
                SubElement(item, _g("additional_image_link")).text = extra

            price_cents = variant_price(product, variant) if variant else product.price_cents
            in_stock = _variant_in_stock(variant) if variant else True
            SubElement(item, _g("availability")).text = "in stock" if in_stock else "out of stock"
            SubElement(item, _g("price")).text = f"{price_cents / 100:.2f} BRL"
            SubElement(item, _g("condition")).text = "new"
            SubElement(item, _g("brand")).text = product.brand or store_name

            if _is_shoe(product.name, paths):
                SubElement(item, _g("google_product_category")).text = _GPC_SHOES
            if product_type:
                SubElement(item, _g("product_type")).text = product_type[:750]

            v_color, v_size = _variant_axes(variant)
            color = product.color_name or v_color or (desc_color.group(1).strip() if desc_color else None)
            if color:
                SubElement(item, _g("color")).text = _nice(color)[:100]
            if v_size:
                SubElement(item, _g("size")).text = v_size[:100]
            SubElement(item, _g("gender")).text = gender
            SubElement(item, _g("age_group")).text = age_group

            barcode = variant.barcode if variant else None
            if barcode:
                SubElement(item, _g("gtin")).text = barcode
            else:
                SubElement(item, _g("identifier_exists")).text = "no"

    return tostring(rss, encoding="utf-8", xml_declaration=True)
