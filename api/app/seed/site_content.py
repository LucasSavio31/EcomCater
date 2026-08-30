"""Semeia páginas institucionais + menus (cabeçalho, rodapé e Categorias).

Inspirado na estrutura de navegação de lojas do tipo catlifestyle.com.br,
adaptado ao catálogo atual.

    python -m app.seed.site_content

Idempotente:
- Páginas: cria as que faltam; NÃO sobrescreve o conteúdo de páginas já
  existentes (só garante que estão publicadas).
- Menus header/footer: reconstrói os itens do zero para bater com a estrutura
  abaixo. As páginas apontadas usam a rota /pagina/<slug>.
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.modules.categories import service as categories_service
from app.modules.categories.models import Category
from app.modules.menus.models import Menu, MenuItem
from app.modules.theme.models import Page

# Itens do menu superior: (rótulo exibido, nome da categoria).
# A categoria é criada no topo se ainda não existir.
_HEADER_ITEMS = (
    ("LANÇAMENTOS", "Lançamentos"),
    ("Masculino", "Masculino"),
    ("Feminino", "Feminino"),
    ("Coturnos", "Coturnos"),
    ("PROMOÇÃO", "Promoção"),
)

logger = logging.getLogger("seed.site_content")

# --------------------------------------------------------------------- páginas
_P = (
    (
        "duvidas",
        "Dúvidas",
        """<h2>Dúvidas frequentes</h2>
<p>Reunimos aqui as perguntas mais comuns sobre pedidos, entrega e pagamento.</p>
<h3>Como acompanho meu pedido?</h3>
<p>Assim que o pedido é enviado, você recebe o código de rastreio por e-mail e
pode acompanhá-lo em <strong>Minha conta &gt; Meus pedidos</strong>.</p>
<h3>Qual o prazo de entrega?</h3>
<p>O prazo aparece no checkout depois que você informa o CEP e varia conforme a
transportadora e a região.</p>
<h3>Posso alterar o endereço depois de comprar?</h3>
<p>Sim, enquanto o pedido ainda não foi despachado. Fale com o nosso
atendimento o quanto antes.</p>""",
    ),
    (
        "garantia-e-cuidados",
        "Garantia e Cuidados",
        """<h2>Garantia</h2>
<p>Todos os produtos têm garantia legal de <strong>90 dias</strong> contra
defeitos de fabricação, contados a partir do recebimento.</p>
<p>A garantia não cobre desgaste natural pelo uso, mau uso, acidentes ou
alterações feitas fora da nossa assistência.</p>
<h2>Cuidados</h2>
<ul>
<li>Higienize com pano levemente úmido e sabão neutro.</li>
<li>Evite deixar o produto exposto ao sol por longos períodos.</li>
<li>Guarde em local seco e arejado.</li>
<li>Não utilize produtos químicos abrasivos.</li>
</ul>""",
    ),
    (
        "troca-e-devolucao",
        "Troca e Devolução",
        """<h2>Troca e Devolução</h2>
<p>Você tem até <strong>7 dias corridos</strong> após o recebimento para
solicitar a devolução por arrependimento, conforme o Código de Defesa do
Consumidor. Para trocas por outro tamanho ou modelo, o prazo é de
<strong>30 dias</strong>.</p>
<h3>Como solicitar</h3>
<ul>
<li>Entre em contato pelo nosso atendimento informando o número do pedido.</li>
<li>O produto deve estar sem uso, com etiquetas e na embalagem original.</li>
<li>Enviaremos as instruções e o código de postagem.</li>
</ul>
<h3>Reembolso</h3>
<p>Após recebermos e conferirmos o produto, o estorno é feito pelo mesmo meio
de pagamento em até 10 dias úteis.</p>""",
    ),
    (
        "politica-de-privacidade",
        "Política de Privacidade",
        """<h2>Política de Privacidade</h2>
<p>Levamos a sério a proteção dos seus dados. Esta política explica o que
coletamos, por que e como você pode exercer seus direitos.</p>
<h3>Dados que coletamos</h3>
<ul>
<li>Cadastro: nome, e-mail, CPF, telefone e endereço.</li>
<li>Pedidos: itens comprados, valores e histórico.</li>
<li>Navegação: cookies para lembrar seu carrinho e melhorar a experiência.</li>
</ul>
<h3>Como usamos</h3>
<p>Para processar pedidos, emitir nota fiscal, calcular frete, prevenir fraude
e, com o seu consentimento, enviar novidades e promoções.</p>
<h3>Seus direitos</h3>
<p>Você pode solicitar acesso, correção ou exclusão dos seus dados pelo nosso
canal de atendimento.</p>""",
    ),
    (
        "formas-de-pagamento",
        "Formas de Pagamento",
        """<h2>Formas de Pagamento</h2>
<ul>
<li><strong>PIX</strong> — aprovação na hora.</li>
<li><strong>Cartão de crédito</strong> — em até 12x (parcelamento conforme as
regras da loja).</li>
<li><strong>Boleto bancário</strong> — compensação em 1 a 2 dias úteis.</li>
</ul>
<h3>Segurança</h3>
<p>Todas as transações são processadas em ambiente criptografado. Não
armazenamos os dados do seu cartão.</p>""",
    ),
)


async def _seed_pages(db: AsyncSession) -> dict[str, str]:
    """Cria as páginas que faltam. Retorna {slug: title} de todas elas."""
    out: dict[str, str] = {}
    for slug, title, body in _P:
        page = await db.scalar(select(Page).where(Page.slug == slug))
        if page:
            page.is_published = True
            logger.info("página já existe: %s", slug)
        else:
            db.add(Page(slug=slug, title=title, body=body, is_published=True))
            logger.info("página criada: %s", slug)
        out[slug] = title
    return out


# --------------------------------------------------------------------- categorias
def _depth(cat: Category) -> int:
    return (cat.path or "").count("/")


async def _main_categories(db: AsyncSession, limit: int = 5) -> list[Category]:
    """As categorias 'principais': raiz e 1º nível, por posição. Só desce para
    níveis mais fundos se não houver categorias suficientes. Até `limit`."""
    cats = list(
        await db.scalars(select(Category).where(Category.is_active.is_(True)))
    )
    cats.sort(key=lambda c: (_depth(c), c.position, c.name.lower()))
    shallow = [c for c in cats if _depth(c) <= 1]
    chosen = shallow if len(shallow) >= 3 else cats
    return chosen[:limit]


def _cat_url(cat: Category) -> str:
    return f"/categoria/{cat.path}" if cat.path else f"/categoria/{cat.slug}"


# --------------------------------------------------------------------- menus
async def _reset_menu(db: AsyncSession, location: str, name: str) -> Menu:
    menu = await db.scalar(select(Menu).where(Menu.location == location))
    if menu:
        for it in await db.scalars(select(MenuItem).where(MenuItem.menu_id == menu.id)):
            await db.delete(it)
        menu.name = name
        menu.is_active = True
    else:
        menu = Menu(location=location, name=name, position=0, is_active=True)
        db.add(menu)
    await db.flush()
    return menu


async def _add(
    db: AsyncSession,
    menu: Menu,
    *,
    label: str,
    position: int,
    parent: MenuItem | None = None,
    category: Category | None = None,
    url: str | None = None,
    page_slug: str | None = None,
    megamenu: bool = False,
    highlight: bool = False,
) -> MenuItem:
    if category is not None:
        link_type, url_val, cat_id = "category", None, category.id
    elif page_slug is not None:
        link_type, url_val, cat_id = "page", f"/pagina/{page_slug}", None
    else:
        link_type, url_val, cat_id = "url", url, None
    item = MenuItem(
        menu_id=menu.id,
        parent_id=parent.id if parent else None,
        label=label,
        link_type=link_type,
        category_id=cat_id,
        url=url_val,
        position=position,
        is_megamenu=megamenu,
        highlight=highlight,
    )
    db.add(item)
    await db.flush()
    return item


async def _ensure_category(db: AsyncSession, name: str, position: int = 0) -> Category:
    """Acha a categoria de topo pelo nome ou cria uma no topo (departamento)."""
    target = name.strip().lower()
    tops = await db.scalars(
        select(Category).where(Category.parent_id.is_(None))
    )
    for c in tops:
        if c.name.strip().lower() == target:
            c.is_active = True
            c.position = position
            return c
    cat = await categories_service.create(
        db, {"name": name, "is_active": True, "position": position}
    )
    logger.info("categoria criada: %s (%s)", name, cat.path)
    return cat


async def _seed_header(db: AsyncSession) -> None:
    menu = await _reset_menu(db, "header", "Menu principal")
    for pos, (label, cat_name) in enumerate(_HEADER_ITEMS):
        cat = await _ensure_category(db, cat_name, position=pos)
        await _add(
            db, menu, label=label, position=pos, category=cat,
            highlight=label.upper() in ("PROMOÇÃO", "PROMOCAO"),
        )


async def _seed_footer(db: AsyncSession, mains: list[Category]) -> None:
    menu = await _reset_menu(db, "footer", "Rodapé")

    async def column(title: str, position: int) -> MenuItem:
        return await _add(db, menu, label=title, position=position)

    # coluna 1 — Institucional
    col1 = await column("Institucional", 0)
    c1 = 0
    for slug, label in (
        ("quem-somos", "Quem Somos"),
        ("duvidas", "Dúvidas"),
        ("garantia-e-cuidados", "Garantia e Cuidados"),
    ):
        page = await db.scalar(select(Page).where(Page.slug == slug))
        if page:
            await _add(db, menu, label=label, position=c1, parent=col1, page_slug=slug)
            c1 += 1

    # coluna 2 — Atendimento
    col2 = await column("Atendimento", 1)
    c2 = 0
    for slug, label in (
        ("troca-e-devolucao", "Troca e Devolução"),
        ("entregas", "Entregas"),
        ("formas-de-pagamento", "Formas de Pagamento"),
        ("politica-de-privacidade", "Política de Privacidade"),
    ):
        page = await db.scalar(select(Page).where(Page.slug == slug))
        if page:
            await _add(db, menu, label=label, position=c2, parent=col2, page_slug=slug)
            c2 += 1

    # coluna 3 — Categorias (principais, automático)
    col3 = await column("Categorias", 2)
    for j, c in enumerate(mains):
        await _add(db, menu, label=c.name, position=j, parent=col3, category=c)


async def run(db: AsyncSession) -> None:
    pages = await _seed_pages(db)
    await db.flush()
    await _seed_header(db)          # cria categorias do menu se faltarem
    await db.flush()
    mains = await _main_categories(db, limit=5)
    await _seed_footer(db, mains)
    await db.commit()
    logger.info(
        "site_content ok — %d páginas, %d categorias principais", len(pages), len(mains)
    )


async def _main() -> None:
    logging.basicConfig(level=logging.INFO)
    async with SessionLocal() as db:
        await run(db)


if __name__ == "__main__":
    asyncio.run(_main())
