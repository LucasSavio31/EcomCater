import { resolveSiteUrl, SITE_NAME } from '@/lib/seo';
import { getTheme } from '@/modules/theme';
import { getCategoryTree, getFeaturedProducts } from '@/modules/catalog/api';
import { getPage, KNOWN_PAGE_SLUGS } from '@/modules/content/api';
import type { CategoryNode } from '@/modules/catalog/types';

/**
 * `/llms.txt` — convenção emergente (llmstxt.org) pra descrever o site em
 * Markdown, resumido e direto, pra assistentes/LLMs entenderem do que se
 * trata sem ter que rastrear/renderizar HTML. Tudo abaixo vem ao vivo do
 * catálogo/tema/páginas — nada hardcoded do nome da loja pra baixo.
 */
export const revalidate = 3600;

function flattenTop(nodes: CategoryNode[], depth = 0): CategoryNode[] {
  const out: CategoryNode[] = [];
  for (const node of nodes) {
    if (node.product_count > 0) out.push(node);
    if (depth < 1) out.push(...flattenTop(node.children, depth + 1));
  }
  return out;
}

function money(cents: number): string {
  return (cents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export async function GET() {
  const [siteUrl, theme, categories, featured] = await Promise.all([
    resolveSiteUrl(),
    getTheme(),
    getCategoryTree(),
    getFeaturedProducts(15),
  ]);

  const storeName = theme.store_name?.trim() || SITE_NAME;
  const lines: string[] = [];

  lines.push(`# ${storeName}`);
  lines.push('');
  lines.push(
    `> Loja online${theme.legal_name ? ` (${theme.legal_name})` : ''} — catálogo, preços e ` +
      'políticas abaixo refletem o estado atual do site.',
  );
  lines.push('');

  if (theme.whatsapp_number || theme.social_json) {
    lines.push('## Contato');
    if (theme.whatsapp_number) lines.push(`- WhatsApp: ${theme.whatsapp_number}`);
    for (const [network, url] of Object.entries(theme.social_json ?? {})) {
      if (url) lines.push(`- ${network}: ${url}`);
    }
    lines.push('');
  }

  const categoryList = flattenTop(categories);
  if (categoryList.length > 0) {
    lines.push('## Categorias');
    for (const c of categoryList) {
      lines.push(`- [${c.name}](${siteUrl}/categoria/${c.path}): ${c.product_count} produtos`);
    }
    lines.push('');
  }

  if (featured.length > 0) {
    lines.push('## Produtos em destaque');
    for (const p of featured) {
      lines.push(`- [${p.name}](${siteUrl}/produto/${p.slug}): ${money(p.price_cents)}`);
    }
    lines.push('');
  }

  const pages = (
    await Promise.all(KNOWN_PAGE_SLUGS.map((slug) => getPage(slug)))
  ).filter((p): p is NonNullable<typeof p> => p !== null);
  if (pages.length > 0) {
    lines.push('## Páginas institucionais');
    for (const p of pages) {
      lines.push(`- [${p.title}](${siteUrl}/pagina/${p.slug})`);
    }
    lines.push('');
  }

  lines.push('## Outros recursos');
  lines.push(`- [Sitemap completo (XML)](${siteUrl}/sitemap.xml)`);
  lines.push(`- [robots.txt](${siteUrl}/robots.txt)`);
  lines.push('');
  lines.push(
    '## Observações',
  );
  lines.push(
    '- Carrinho, checkout, conta e busca são páginas privadas/dinâmicas por ' +
      'usuário — não estão listadas aqui nem no sitemap.',
  );
  lines.push('- Preços e estoque mudam com frequência; confira sempre a página do produto.');

  return new Response(lines.join('\n') + '\n', {
    headers: {
      'Content-Type': 'text/markdown; charset=utf-8',
      'Cache-Control': 'public, max-age=0, s-maxage=3600, stale-while-revalidate=86400',
    },
  });
}
