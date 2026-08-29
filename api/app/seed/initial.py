"""Seed inicial — idempotente. Roda via `python -m app.seed.run` (ou `make seed`)."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.module_registry import all_specs
from app.core.security import hash_password
from app.models import (
    AdminUser,
    Banner,
    Menu,
    MenuItem,
    ModuleRow,
    Page,
    SmtpSettings,
    StoreSettings,
    ThemeSettings,
)

logger = logging.getLogger("seed")


async def seed_admin(db: AsyncSession) -> None:
    exists = await db.scalar(select(AdminUser).where(AdminUser.email == settings.admin_email))
    if exists:
        logger.info("admin já existe: %s", settings.admin_email)
        return
    db.add(
        AdminUser(
            email=settings.admin_email,
            name=settings.admin_name,
            password_hash=hash_password(settings.admin_password),
            role="super_admin",
            must_change_password=True,
            is_active=True,
        )
    )
    logger.info("admin padrão criado: %s (troca de senha obrigatória)", settings.admin_email)


async def seed_singletons(db: AsyncSession) -> None:
    now = datetime.now(UTC)
    if not await db.get(ThemeSettings, 1):
        db.add(ThemeSettings(id=1, updated_at=now))
        logger.info("theme_settings (paleta neutra) criado")
    if not await db.get(StoreSettings, 1):
        db.add(
            StoreSettings(
                id=1,
                store_name="Minha Loja",
                payment_flags_json=["visa", "mastercard", "amex", "elo", "hipercard", "pix", "boleto"],
                updated_at=now,
            )
        )
        logger.info("store_settings criado")
    if not await db.get(SmtpSettings, 1):
        db.add(SmtpSettings(id=1, updated_at=now))
        logger.info("smtp_settings criado (vazio)")


async def seed_modules(db: AsyncSession) -> None:
    existing = {r.slug for r in await db.scalars(select(ModuleRow))}
    now = datetime.now(UTC)
    for spec in all_specs():
        if spec.slug in existing:
            continue
        db.add(
            ModuleRow(
                slug=spec.slug,
                enabled=spec.default_enabled,
                config_json=dict(spec.default_config),
                updated_at=now,
            )
        )
    logger.info("registro de módulos sincronizado (%d specs)", len(all_specs()))


async def seed_menus(db: AsyncSession) -> None:
    if await db.scalar(select(Menu).limit(1)):
        logger.info("menus já existem — pulando")
        return
    header = Menu(location="header", name="Menu principal", position=0, is_active=True)
    footer = Menu(location="footer", name="Rodapé", position=0, is_active=True)
    db.add_all([header, footer])
    await db.flush()

    db.add_all(
        [
            MenuItem(menu_id=header.id, label="LANÇAMENTOS", link_type="url", url="/categoria/lancamentos", position=0, highlight=False),
            MenuItem(menu_id=header.id, label="ATÉ 50% OFF", link_type="url", url="/categoria/ofertas", position=1, highlight=True),
            MenuItem(menu_id=footer.id, label="Quem Somos", link_type="page", url="/quem-somos", position=0),
            MenuItem(menu_id=footer.id, label="Política de Privacidade", link_type="page", url="/politica-de-privacidade", position=1),
            MenuItem(menu_id=footer.id, label="Trocas e Devoluções", link_type="page", url="/trocas-e-devolucoes", position=2),
            MenuItem(menu_id=footer.id, label="Fale Conosco", link_type="page", url="/fale-conosco", position=3),
        ]
    )
    logger.info("menus header/footer básicos criados")


async def seed_content(db: AsyncSession) -> None:
    now = datetime.now(UTC)
    if not await db.scalar(select(Page).limit(1)):
        for slug, title in [
            ("quem-somos", "Quem Somos"),
            ("politica-de-privacidade", "Política de Privacidade"),
            ("politica-de-vendas", "Política de Vendas"),
            ("trocas-e-devolucoes", "Trocas e Devoluções"),
            ("como-comprar", "Como Comprar"),
            ("entregas", "Entregas"),
            ("fale-conosco", "Fale Conosco"),
        ]:
            db.add(
                Page(
                    slug=slug,
                    title=title,
                    body=f"<h1>{title}</h1><p>Conteúdo a configurar no admin.</p>",
                    is_published=True,
                    updated_at=now,
                )
            )
        logger.info("páginas institucionais criadas")
    if not await db.scalar(select(Banner).limit(1)):
        db.add_all(
            [
                Banner(slot="hero", title="Nova Coleção", link_url="/categoria/feminino", position=0, is_active=True),
                Banner(slot="showcase", title="Mais Vendidos", link_url="/categoria/feminino", position=0, is_active=True),
                Banner(slot="showcase", title="Acessórios", link_url="/categoria/acessorios", position=1, is_active=True),
            ]
        )
        logger.info("banners de exemplo criados")


async def run_all(db: AsyncSession) -> None:
    await seed_admin(db)
    await seed_singletons(db)
    await seed_modules(db)
    await seed_menus(db)
    await seed_content(db)
    await db.commit()
    logger.info("seed concluído.")
