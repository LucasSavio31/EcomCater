"""Semeia a navegação da loja (categorias + páginas + menus) no estilo de
lojas de calçado tipo catlifestyle.com.br (Cat Footwear): departamentos
Masculino/Feminino com mega menu, mais Botas, Tênis, Acessórios, Novidades e
Outlet; rodapé em 4 colunas (Institucional / Ajuda / Políticas / Categorias).

    python -m app.seed.site_content

Idempotente:
- Categorias: cria as que faltam (por nome + pai), nunca apaga.
- Páginas: cria as que faltam; não sobrescreve conteúdo já existente.
- Menus header/footer: reconstrói os itens para bater com a estrutura abaixo.
- Ao final, distribui os produtos sem categoria entre as folhas, só para as
  vitrines não ficarem vazias (nunca mexe em produto que já tem categoria).
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
from app.modules.products.models import Product, ProductCategory
from app.modules.theme.models import Page, ThemeSettings

logger = logging.getLogger("seed.site_content")

# ------------------------------------------------------------------ categorias
# (departamento, [subcategorias])
_TREE: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Masculino", ("Botas", "Coturnos", "Tênis", "Sapatênis", "Casual", "Sandálias")),
    ("Feminino", ("Botas", "Coturnos", "Tênis", "Casual", "Rasteiras")),
    ("Acessórios", ("Meias", "Cadarços", "Palmilhas", "Kit de Cuidados")),
)
# categorias de topo sem subcategoria
_FLAT_TOP = ("Botas", "Tênis", "Novidades", "Outlet")

# menu superior: (rótulo, nome da categoria de topo, megamenu?, destaque?)
_HEADER = (
    ("NOVIDADES", "Novidades", False, False),
    ("MASCULINO", "Masculino", True, False),
    ("FEMININO", "Feminino", True, False),
    ("BOTAS", "Botas", False, False),
    ("TÊNIS", "Tênis", False, False),
    ("ACESSÓRIOS", "Acessórios", False, False),
    ("OUTLET", "Outlet", False, True),
)

# ------------------------------------------------------------------ páginas
_PAGES: tuple[tuple[str, str, str], ...] = (
    (
        "quem-somos",
        "Quem Somos",
        """<h2>Quem somos</h2>
<p>Nascemos para levar calçados que unem resistência e estilo do dia a dia
urbano ao off-road. Cada par é pensado para durar: materiais selecionados,
solados que encaram qualquer terreno e um caimento que combina com tudo.</p>
<p>Trabalhamos com curadoria própria, atendimento humano e uma política de
trocas simples — porque comprar calçado online também tem que ser confortável.</p>""",
    ),
    (
        "nossas-lojas",
        "Nossas Lojas",
        """<h2>Nossas lojas</h2>
<p>Além da loja online, você encontra nossos produtos em pontos de venda
parceiros pelo Brasil. Em breve divulgaremos aqui os endereços e horários das
lojas físicas.</p>
<p>Para atacado e representação, fale com <strong>comercial@loja.local</strong>.</p>""",
    ),
    (
        "trabalhe-conosco",
        "Trabalhe Conosco",
        """<h2>Trabalhe conosco</h2>
<p>Quer fazer parte do time? Envie seu currículo para
<strong>rh@loja.local</strong> com a vaga de interesse no assunto.</p>
<p>Estamos sempre de olho em pessoas para atendimento, logística, conteúdo e
tecnologia.</p>""",
    ),
    (
        "central-de-atendimento",
        "Central de Atendimento",
        """<h2>Central de atendimento</h2>
<p>Precisa de ajuda com um pedido? Estamos aqui.</p>
<ul>
<li><strong>E-mail:</strong> atendimento@loja.local</li>
<li><strong>WhatsApp:</strong> (11) 90000-0000</li>
<li><strong>Horário:</strong> segunda a sexta, das 9h às 18h</li>
</ul>
<p>Tenha o número do pedido em mãos para agilizar o atendimento.</p>""",
    ),
    (
        "duvidas",
        "Dúvidas Frequentes",
        """<h2>Dúvidas frequentes</h2>
<h3>Como acompanho meu pedido?</h3>
<p>Assim que ele é despachado, você recebe o código de rastreio por e-mail e
pode acompanhá-lo em <strong>Minha conta &gt; Meus pedidos</strong>.</p>
<h3>Qual o prazo de entrega?</h3>
<p>O prazo aparece no checkout depois que você informa o CEP e varia conforme a
transportadora e a região.</p>
<h3>Como escolher a numeração certa?</h3>
<p>Cada produto tem uma tabela de medidas na própria página. Na dúvida entre
dois números, recomendamos o maior.</p>
<h3>Posso trocar se não servir?</h3>
<p>Pode. A primeira troca por numeração é facilitada — veja a página
<em>Trocas e Devoluções</em>.</p>""",
    ),
    (
        "troca-e-devolucao",
        "Trocas e Devoluções",
        """<h2>Trocas e devoluções</h2>
<p>Você tem até <strong>7 dias corridos</strong> após o recebimento para
solicitar devolução por arrependimento (Código de Defesa do Consumidor). Para
troca por outro tamanho ou modelo, o prazo é de <strong>30 dias</strong>.</p>
<h3>Como solicitar</h3>
<ul>
<li>Fale com o atendimento informando o número do pedido.</li>
<li>O produto deve estar sem uso, com etiquetas e na caixa original.</li>
<li>Enviamos as instruções e o código de postagem.</li>
</ul>
<h3>Reembolso</h3>
<p>Depois de recebermos e conferirmos o produto, o estorno é feito pelo mesmo
meio de pagamento em até 10 dias úteis.</p>""",
    ),
    (
        "garantia-e-cuidados",
        "Garantia e Cuidados",
        """<h2>Garantia</h2>
<p>Todos os produtos têm garantia legal de <strong>90 dias</strong> contra
defeitos de fabricação, a contar do recebimento. A garantia não cobre desgaste
natural pelo uso, mau uso, acidentes ou reparos feitos fora da nossa
assistência.</p>
<h2>Cuidados com o calçado</h2>
<ul>
<li>Limpe com pano levemente úmido e sabão neutro; evite imersão.</li>
<li>Deixe secar à sombra, longe de fontes de calor.</li>
<li>Use impermeabilizante adequado ao material (couro, camurça, têxtil).</li>
<li>Guarde em local seco e arejado, de preferência com forma ou papel dentro.</li>
</ul>""",
    ),
    (
        "formas-de-pagamento",
        "Formas de Pagamento",
        """<h2>Formas de pagamento</h2>
<ul>
<li><strong>PIX</strong> — aprovação na hora, com possível desconto.</li>
<li><strong>Cartão de crédito</strong> — parcelamento conforme as regras da loja.</li>
<li><strong>Boleto bancário</strong> — compensação em 1 a 2 dias úteis.</li>
</ul>
<h3>Segurança</h3>
<p>Todas as transações passam por ambiente criptografado e antifraude. Não
armazenamos os dados do seu cartão.</p>""",
    ),
    (
        "politica-de-privacidade",
        "Política de Privacidade",
        """<h2>Política de Privacidade</h2>
<p>Esta política explica quais dados coletamos, por que e como você exerce seus
direitos, em linha com a LGPD.</p>
<h3>Dados que coletamos</h3>
<ul>
<li>Cadastro: nome, e-mail, CPF, telefone e endereço.</li>
<li>Pedidos: itens, valores e histórico.</li>
<li>Navegação: cookies para lembrar seu carrinho e melhorar a experiência.</li>
</ul>
<h3>Como usamos</h3>
<p>Para processar pedidos, emitir nota fiscal, calcular frete, prevenir fraude
e — com o seu consentimento — enviar novidades.</p>
<h3>Seus direitos</h3>
<p>Você pode pedir acesso, correção ou exclusão dos seus dados pelo nosso canal
de atendimento.</p>""",
    ),
    (
        "politica-de-vendas",
        "Política de Vendas",
        """<h2>Política de Vendas</h2>
<p>Os preços e condições de pagamento exibidos são válidos apenas para compras
neste site e podem ser alterados sem aviso prévio. Imagens são ilustrativas.</p>
<h3>Confirmação do pedido</h3>
<p>O pedido é confirmado após a aprovação do pagamento. Em caso de divergência
de preço por erro evidente, entraremos em contato antes de faturar.</p>
<h3>Prazos</h3>
<p>O prazo de entrega começa a contar a partir da aprovação do pagamento e da
disponibilidade do item em estoque.</p>""",
    ),
    (
        "termos-de-uso",
        "Termos de Uso",
        """<h2>Termos de Uso</h2>
<p>Ao navegar e comprar neste site, você concorda com estes termos. O conteúdo
(textos, imagens e marcas) é protegido e não pode ser reproduzido sem
autorização.</p>
<h3>Conta</h3>
<p>Você é responsável por manter a confidencialidade da sua senha e por todas as
atividades realizadas na sua conta.</p>
<h3>Uso adequado</h3>
<p>É proibido usar o site para fins ilícitos, tentar burlar mecanismos de
segurança ou automatizar acessos sem autorização.</p>""",
    ),
)

_FOOTER = (
    (
        "Institucional",
        (
            ("Quem Somos", "quem-somos"),
            ("Nossas Lojas", "nossas-lojas"),
            ("Trabalhe Conosco", "trabalhe-conosco"),
        ),
    ),
    (
        "Ajuda",
        (
            ("Central de Atendimento", "central-de-atendimento"),
            ("Dúvidas Frequentes", "duvidas"),
            ("Trocas e Devoluções", "troca-e-devolucao"),
            ("Garantia e Cuidados", "garantia-e-cuidados"),
            ("Formas de Pagamento", "formas-de-pagamento"),
        ),
    ),
    (
        "Políticas",
        (
            ("Política de Privacidade", "politica-de-privacidade"),
            ("Política de Vendas", "politica-de-vendas"),
            ("Termos de Uso", "termos-de-uso"),
        ),
    ),
)


# --------------------------------------------------------------------- helpers
async def _get_or_create_category(
    db: AsyncSession, name: str, *, parent: Category | None, position: int
) -> Category:
    parent_id = parent.id if parent else None
    rows = await db.scalars(select(Category).where(Category.parent_id == parent_id) if parent_id
                            else select(Category).where(Category.parent_id.is_(None)))
    for c in rows:
        if c.name.strip().lower() == name.strip().lower():
            c.is_active = True
            c.position = position
            return c
    cat = await categories_service.create(
        db, {"name": name, "parent_id": str(parent_id) if parent_id else None,
             "position": position, "is_active": True}
    )
    logger.info("categoria criada: %s (%s)", name, cat.path)
    return cat


async def _seed_categories(db: AsyncSession) -> dict[str, Category]:
    """Cria a árvore. Retorna {nome_do_topo: Category} das categorias de topo."""
    tops: dict[str, Category] = {}
    pos = 0
    for dept_name, subs in _TREE:
        dept = await _get_or_create_category(db, dept_name, parent=None, position=pos)
        tops[dept_name] = dept
        pos += 1
        for j, sub in enumerate(subs):
            await _get_or_create_category(db, sub, parent=dept, position=j)
    for flat in _FLAT_TOP:
        if flat not in tops:
            tops[flat] = await _get_or_create_category(db, flat, parent=None, position=pos)
            pos += 1
    await db.flush()
    return tops


_PLACEHOLDER_MARK = "configurar no admin"


async def _seed_pages(db: AsyncSession) -> None:
    for slug, title, body in _PAGES:
        page = await db.scalar(select(Page).where(Page.slug == slug))
        if page:
            page.is_published = True
            # substitui só o texto-espaço-reservado do seed base
            if not page.body or _PLACEHOLDER_MARK in page.body:
                page.title = title
                page.body = body
        else:
            db.add(Page(slug=slug, title=title, body=body, is_published=True))
            logger.info("página criada: %s", slug)
    await db.flush()


async def _reset_menu(db: AsyncSession, location: str, name: str) -> Menu:
    menu = await db.scalar(select(Menu).where(Menu.location == location))
    if menu:
        for it in await db.scalars(select(MenuItem).where(MenuItem.menu_id == menu.id)):
            await db.delete(it)
        await db.flush()
        menu.name = name
        menu.is_active = True
    else:
        menu = Menu(location=location, name=name, position=0, is_active=True)
        db.add(menu)
    await db.flush()
    return menu


async def _add_item(
    db: AsyncSession, menu: Menu, *, label: str, position: int,
    parent: MenuItem | None = None, category: Category | None = None,
    page_slug: str | None = None, url: str | None = None,
    megamenu: bool = False, highlight: bool = False,
) -> MenuItem:
    if category is not None:
        link_type, url_val, cat_id = "category", None, category.id
    elif page_slug is not None:
        link_type, url_val, cat_id = "page", f"/pagina/{page_slug}", None
    else:
        link_type, url_val, cat_id = "url", url or "#", None
    item = MenuItem(
        menu_id=menu.id, parent_id=parent.id if parent else None, label=label,
        link_type=link_type, category_id=cat_id, url=url_val, position=position,
        is_megamenu=megamenu, highlight=highlight,
    )
    db.add(item)
    await db.flush()
    return item


async def _seed_header(db: AsyncSession, tops: dict[str, Category]) -> None:
    menu = await _reset_menu(db, "header", "Menu principal")
    for pos, (label, cat_name, mega, hi) in enumerate(_HEADER):
        cat = tops.get(cat_name)
        if not cat:
            continue
        parent = await _add_item(
            db, menu, label=label, position=pos, category=cat, megamenu=mega, highlight=hi
        )
        if mega:
            subs = list(
                await db.scalars(
                    select(Category).where(Category.parent_id == cat.id).order_by(Category.position)
                )
            )
            for j, sub in enumerate(subs):
                await _add_item(db, menu, label=sub.name, position=j, parent=parent, category=sub)


def _depth(c: Category) -> int:
    return (c.path or "").count("/")


async def _seed_footer(db: AsyncSession) -> None:
    menu = await _reset_menu(db, "footer", "Rodapé")
    pos = 0
    for title, links in _FOOTER:
        col = await _add_item(db, menu, label=title, position=pos)
        pos += 1
        for j, (label, slug) in enumerate(links):
            page = await db.scalar(select(Page).where(Page.slug == slug))
            if page:
                await _add_item(db, menu, label=label, position=j, parent=col, page_slug=slug)

    # coluna Categorias — as mesmas categorias de topo do menu superior
    by_name = {
        c.name.strip().lower(): c
        for c in await db.scalars(select(Category).where(Category.parent_id.is_(None)))
    }
    col = await _add_item(db, menu, label="Categorias", position=pos)
    j = 0
    for _label, cat_name, _mega, _hi in _HEADER:
        c = by_name.get(cat_name.strip().lower())
        if c and c.is_active:
            await _add_item(db, menu, label=c.name, position=j, parent=col, category=c)
            j += 1


async def _distribute_products(db: AsyncSession, tops: dict[str, Category]) -> int:
    """Dá uma categoria às vitrines: para cada produto SEM categoria principal,
    escolhe uma folha (Masculino/Feminino > algo) em rodízio. Não altera produto
    que já tem categoria."""
    leaves: list[Category] = []
    for dept in ("Masculino", "Feminino"):
        d = tops.get(dept)
        if not d:
            continue
        leaves += list(
            await db.scalars(select(Category).where(Category.parent_id == d.id).order_by(Category.position))
        )
    if not leaves:
        return 0
    orphans = list(await db.scalars(select(Product).where(Product.category_id.is_(None))))
    changed = 0
    for i, p in enumerate(orphans):
        leaf = leaves[i % len(leaves)]
        p.category_id = leaf.id
        db.add(ProductCategory(product_id=p.id, category_id=leaf.id))
        # também vincula ao departamento pai, para a vitrine do topo não ficar vazia
        if leaf.parent_id:
            db.add(ProductCategory(product_id=p.id, category_id=leaf.parent_id))
        changed += 1
    return changed


_KNOWN_TOPS = {n.lower() for n, _ in _TREE} | {n.lower() for n in _FLAT_TOP}


async def _deactivate_stray_tops(db: AsyncSession) -> None:
    """Desliga (não apaga) categorias de topo que não fazem parte desta árvore e
    que não têm nenhum produto — ex.: 'Calçados' criada por outro seed."""
    tops = await db.scalars(select(Category).where(Category.parent_id.is_(None)))
    for c in tops:
        if c.name.strip().lower() in _KNOWN_TOPS:
            continue
        from app.modules.products.service import _descendant_category_ids

        ids = await _descendant_category_ids(db, c.id)
        used = await db.scalar(
            select(Product.id).where(
                (Product.category_id.in_(ids))
                | (Product.id.in_(select(ProductCategory.product_id).where(ProductCategory.category_id.in_(ids))))
            ).limit(1)
        )
        if used:
            continue
        c.is_active = False
        for child in await db.scalars(select(Category).where(Category.parent_id == c.id)):
            child.is_active = False
        logger.info("categoria de topo fora da árvore desativada: %s", c.name)
    await db.flush()


_DEFAULT_POPUP_TITLE = "Cadastre-se para 10% OFF na primeira compra"


async def _seed_lead_popup(db: AsyncSession) -> None:
    """Liga o popup de captura de leads com a chamada padrão da loja. Só mexe
    se ainda estiver no texto-padrão do seed base (não sobrescreve ajuste feito
    no admin)."""
    t = await db.get(ThemeSettings, 1)
    if not t:
        return
    t.lead_popup_enabled = True
    t.lead_capture_enabled = True
    if (t.lead_popup_title or "").strip() in ("", _DEFAULT_POPUP_TITLE):
        t.lead_popup_title = "Cadastre-se e ganhe promoções e cupons exclusivos"
        t.lead_popup_subtitle = (
            "Receba as melhores ofertas e um cupom de boas-vindas direto no seu e-mail."
        )
    await db.flush()


async def run(db: AsyncSession) -> None:
    tops = await _seed_categories(db)
    await _deactivate_stray_tops(db)
    await _seed_pages(db)
    await _seed_lead_popup(db)
    await _seed_header(db, tops)
    await _seed_footer(db)
    moved = await _distribute_products(db, tops)
    await db.commit()
    logger.info(
        "site_content ok — %d páginas, %d categorias de topo, %d produtos categorizados",
        len(_PAGES), len(tops), moved,
    )


async def _main() -> None:
    logging.basicConfig(level=logging.INFO)
    import app.models  # noqa: F401 - registra todos os mappers
    from app.bootstrap import discover_modules

    discover_modules()
    async with SessionLocal() as db:
        await run(db)


if __name__ == "__main__":
    asyncio.run(_main())
