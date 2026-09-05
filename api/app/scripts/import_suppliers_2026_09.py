"""Cadastro dos 3 novos fornecedores (Netony, Jose Reis, BR Drop) a partir das
fotos em C:\\Users\\lsavy\\OneDrive\\imagens\\catoficial_scraper\\imagens_calcados.

Cada subpasta "Modelo X - Cor Y - Tipo - Genero - Marca ABC" é UMA COR de um
modelo; cores do mesmo modelo/tipo viram produtos irmãos (color_group_id) com
eixo de numeração 38–44 (estoque ilimitado), reaproveitando a tabela de
medidas "Masculino" e as categorias já cadastradas.

NUNCA toca em produto existente — se o sku_root já existe, a cor é pulada.
Idempotente: pode rodar de novo sem duplicar.

    cd api && ./.venv/Scripts/python.exe -m app.scripts.import_suppliers_2026_09
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import unicodedata
import uuid
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.categories.models import Category
from app.modules.products import service as product_service
from app.modules.products import service_variants
from app.modules.products.models import (
    Product,
    ProductImage,
    VariantOptionType,
    VariantOptionValue,
)
from app.modules.size_charts.models import SizeChart
from app.shared.images import process_image
from app.shared.slugify import make_slug

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scripts.import_suppliers_2026_09")

BASE_DIR = Path(
    os.environ.get("SUPPLIER_IMAGES_DIR")
    or r"C:\Users\lsavy\OneDrive\imagens\catoficial_scraper\imagens_calcados"
)

SIZES = ["38", "39", "40", "41", "42", "43", "44"]

COMMON = {
    "compare_at_price_cents": 49990,
    "installments_max": 10,
    "weight_grams": 2500,
    "length_mm": 450,
    "width_mm": 350,
    "height_mm": 150,
}

SUPPLIERS = [
    {"folder": "Fornecedor Netony", "supplier": "Netony", "price_cents": 24990, "cost_cents": 14500},
    {"folder": "Fornecedor Jose Reis", "supplier": "Jose Reis", "price_cents": 24990, "cost_cents": 15000},
    {"folder": "Fornecedor BR Drop", "supplier": "BR Drop", "price_cents": 26990, "cost_cents": 16000},
]

# "Nome" do produto (CAIXA ALTA) — mesmo padrão dos NTN já cadastrados
# (ex.: "BOTA COTURNO 2021 MARINHO", "TENIS 2085 AVELA").
NAME_TIPO_LABEL = {"bota": "BOTA", "coturno": "BOTA COTURNO", "tenis": "TENIS"}
# Palavra usada no bullet "Tipo:" da descrição (minúscula, com acento).
DESC_TIPO_WORD = {"bota": "bota", "coturno": "bota", "tenis": "tênis"}
TIPO_SLUG = {"bota": "botas", "tenis": "tenis", "coturno": "coturnos"}
GENERO_LETRA = {"masculino": "M", "feminino": "F"}

_SHORT_DESCRIPTION = "Cabedal respirável, forro acolchoado e solado com boa tração."

_FOLDER_RE = re.compile(
    r"^Modelo\s+(?P<modelo>.+?)\s+-\s+Cor\s+(?P<cor>.+?)\s+-\s+(?P<tipo>.+?)\s+-\s+(?P<genero>.+?)\s+-\s+Marca\s+(?P<marca>.+)$",
    re.IGNORECASE,
)
_NUM_SUFFIX_RE = re.compile(r"_(\d+)\.\w+$")


def _parse_folder(name: str) -> dict | None:
    m = _FOLDER_RE.match(name.strip())
    if not m:
        return None
    return {
        "modelo": m.group("modelo").strip(),
        "cor": m.group("cor").strip(),
        "tipo": m.group("tipo").strip().lower(),
        "genero": m.group("genero").strip().lower(),
        "marca": m.group("marca").strip(),
    }


def _image_sort_key(path: Path) -> int:
    m = _NUM_SUFFIX_RE.search(path.name)
    return int(m.group(1)) if m else 0


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _descricao(tipo: str, name: str, modelo: str, cor_raw: str) -> tuple[str, str]:
    """Mesmo formato dos produtos NTN já cadastrados: parágrafo fixo + bullets
    genéricos + bullets de "ficha técnica" (modelo/tipo/cor)."""
    peca = DESC_TIPO_WORD.get(tipo, "bota")
    artigo = "um" if peca == "tênis" else "uma"
    html = (
        f"<p>{name} é {artigo} {peca} casual para o dia a dia. {_SHORT_DESCRIPTION}</p>"
        "<ul>"
        "<li>Fechamento em cadarço</li>"
        "<li>Solado de borracha</li>"
        "<li>Palmilha removível</li>"
        f"<li>Nome modelo: {modelo}</li>"
        f"<li>Tipo: {peca}</li>"
        f"<li>Cor: {cor_raw.lower()}</li>"
        "<li>Solado: Borracha antiderrapante</li>"
        "<li>Forro antitranspirante</li>"
        "<li>Palmilha removível</li>"
        "</ul>"
    )
    return _SHORT_DESCRIPTION, html


async def _category_id(db, genero_slug: str, tipo_slug: str) -> uuid.UUID | None:
    path = f"{genero_slug}/{tipo_slug}"
    cat = await db.scalar(select(Category).where(Category.path == path))
    if not cat:
        logger.warning("categoria '%s' não encontrada — pulando", path)
        return None
    return cat.id


async def _size_chart_id(db) -> uuid.UUID | None:
    chart = await db.scalar(select(SizeChart).where(SizeChart.name == "Masculino"))
    return chart.id if chart else None


async def run() -> dict:
    counts = {"criados": 0, "pulados_existentes": 0, "grupos": 0}
    async with SessionLocal() as db:
        size_chart_id = await _size_chart_id(db)
        if not size_chart_id:
            logger.warning("tabela de medidas 'Masculino' não encontrada — produtos ficarão sem size_chart_id")

        for sup in SUPPLIERS:
            folder = BASE_DIR / sup["folder"]
            if not folder.is_dir():
                logger.warning("pasta não encontrada: %s", folder)
                continue

            # agrupa subpastas por (modelo, tipo, genero) -> lista de (cor, path)
            groups: dict[tuple[str, str, str], list[tuple[str, Path]]] = {}
            marca_code = None
            for sub in sorted(folder.iterdir()):
                if not sub.is_dir():
                    continue
                parsed = _parse_folder(sub.name)
                if not parsed:
                    logger.warning("pasta com nome fora do padrão, ignorada: %s", sub.name)
                    continue
                marca_code = parsed["marca"]
                key = (parsed["modelo"], parsed["tipo"], parsed["genero"])
                groups.setdefault(key, []).append((parsed["cor"], sub))

            for (modelo, tipo, genero), colors in groups.items():
                name_tipo = NAME_TIPO_LABEL.get(tipo, tipo.upper())
                tipo_slug = TIPO_SLUG.get(tipo, make_slug(tipo))
                genero_slug = make_slug(genero)
                genero_letra = GENERO_LETRA.get(genero, genero[:1].upper())
                category_id = await _category_id(db, genero_slug, tipo_slug)

                group_gid = uuid.uuid4() if len(colors) > 1 else None
                created_this_group = 0

                for cor_raw, sub in colors:
                    cor_ascii_upper = _strip_accents(cor_raw).upper()
                    cor_sku = cor_ascii_upper.replace(" ", "_").replace("-", "_")
                    modelo_upper = _strip_accents(modelo).upper()
                    sku_root = f"{marca_code}-{modelo_upper}-{cor_sku}-{genero_letra}"

                    existing = await db.scalar(select(Product.id).where(Product.sku_root == sku_root))
                    if existing:
                        counts["pulados_existentes"] += 1
                        continue

                    name = f"{name_tipo} {modelo_upper} {cor_ascii_upper}"
                    short_desc, desc_html = _descricao(tipo, name, modelo, cor_raw)

                    product = await product_service.create(
                        db,
                        {
                            "name": name,
                            "sku_root": sku_root,
                            "short_description": short_desc,
                            "description": desc_html,
                            "brand": marca_code,
                            "supplier": sup["supplier"],
                            "category_id": str(category_id) if category_id else None,
                            "size_chart_id": str(size_chart_id) if size_chart_id else None,
                            "color_name": cor_ascii_upper,
                            "color_group_id": group_gid,
                            "status": "active",
                            "is_featured": True,
                            "price_cents": sup["price_cents"],
                            "cost_cents": sup["cost_cents"],
                            **COMMON,
                        },
                    )
                    await db.flush()
                    product_id = str(product.id)

                    await service_variants.replace_option_types(
                        db,
                        product_id,
                        [{"name": "Numeração", "is_size": True, "values": [{"value": s} for s in SIZES]}],
                    )
                    await db.flush()
                    db.expunge_all()

                    option_values = list(
                        await db.scalars(
                            select(VariantOptionValue)
                            .join(VariantOptionType, VariantOptionValue.option_type_id == VariantOptionType.id)
                            .where(VariantOptionType.product_id == uuid.UUID(product_id))
                            .order_by(VariantOptionValue.position)
                        )
                    )
                    for k, ov in enumerate(option_values):
                        await service_variants.upsert_variant(
                            db,
                            product_id,
                            {
                                "sku": f"{sku_root}-{ov.value}",
                                "option_value_ids": [str(ov.id)],
                                "stock_qty": None,  # ilimitado
                                "position": k,
                            },
                        )

                    product = await db.get(Product, uuid.UUID(product_id))
                    images = sorted(
                        [p for p in sub.iterdir() if p.is_file()], key=_image_sort_key
                    )
                    for j, img_path in enumerate(images):
                        processed = process_image(img_path.read_bytes(), img_path.name, prefix="products")
                        db.add(
                            ProductImage(
                                product_id=product.id,
                                alt=f"{name} — foto {j + 1}",
                                position=j,
                                is_primary=(j == 0),
                                original_filename=processed.original_filename,
                                original_width=processed.original_width,
                                original_height=processed.original_height,
                                thumb_key=processed.thumb_key,
                                medium_key=processed.medium_key,
                                zoom_key=processed.zoom_key,
                            )
                        )

                    await db.commit()
                    counts["criados"] += 1
                    created_this_group += 1
                    logger.info("criado: %s (sku_root=%s, %d fotos)", name, sku_root, len(images))

                if created_this_group:
                    counts["grupos"] += 1

    return counts


if __name__ == "__main__":
    result = asyncio.run(run())
    print("import de fornecedores concluído:", result)
