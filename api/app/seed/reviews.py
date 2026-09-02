"""Semeia avaliações aprovadas de demonstração — para os cards mostrarem
estrelas e a PDP mostrar nota agregada. Idempotente: pula produtos que já
têm avaliação."""
from __future__ import annotations

import asyncio
import logging
import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.modules.products.models import Product, ProductReview

logger = logging.getLogger("seed.reviews")

_NAMES = ["Ana P.", "Carlos M.", "Juliana R.", "Rafael S.", "Beatriz L.", "Marcos A.",
          "Fernanda C.", "Diego T.", "Patrícia N.", "Bruno O."]
_POS = [
    (5, "Muito confortável", "Chegou rápido e é exatamente como nas fotos. Calçou perfeito."),
    (5, "Recomendo", "Já é o segundo par que compro. Qualidade excelente pelo preço."),
    (4, "Bom, mas veio apertado", "Gostei bastante do acabamento. Sugiro pegar um número acima."),
    (5, "Top", "Solado firme, não escorrega. Uso pra trabalhar o dia todo sem cansar."),
    (4, "Bonito", "Visual muito bom, combina com tudo. Tirei uma estrela pela demora do frete."),
    (5, "Vale a pena", "Material parece durável, costura reforçada. Entrega no prazo."),
]


async def run(db: AsyncSession) -> None:
    prods = list(await db.scalars(select(Product).where(Product.status == "active")))
    created = 0
    for p in prods:
        has = await db.scalar(
            select(func.count()).select_from(ProductReview).where(ProductReview.product_id == p.id)
        )
        if has:
            continue
        n = random.randint(2, 5)
        for _ in range(n):
            r, title, bodytext = random.choice(_POS)
            db.add(
                ProductReview(
                    product_id=p.id,
                    author_name=random.choice(_NAMES),
                    rating=r,
                    title=title,
                    body=bodytext,
                    status="approved",
                    created_at=datetime.now(UTC) - timedelta(days=random.randint(1, 90)),
                )
            )
            created += 1
        await db.flush()
        avg = await db.scalar(
            select(func.avg(ProductReview.rating)).where(
                ProductReview.product_id == p.id, ProductReview.status == "approved"
            )
        )
        cnt = await db.scalar(
            select(func.count()).select_from(ProductReview).where(
                ProductReview.product_id == p.id, ProductReview.status == "approved"
            )
        )
        p.rating_avg = round(float(avg), 2) if avg else 0
        p.rating_count = int(cnt or 0)
    await db.commit()
    logger.info("reviews: %d avaliações criadas", created)


async def _main() -> None:
    logging.basicConfig(level=logging.INFO)
    import app.models  # noqa: F401 - registra todos os mappers (FK users, etc.)

    async with SessionLocal() as db:
        await run(db)


if __name__ == "__main__":
    asyncio.run(_main())
