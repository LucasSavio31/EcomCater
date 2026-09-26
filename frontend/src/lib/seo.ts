/**
 * Helpers de SEO.
 *
 * Multi-domínio: canonical/og:url saem RELATIVOS aqui e o `metadataBase` vem
 * do layout de cada domínio (`app/[site]/layout.tsx`) — o Next resolve pra
 * URL absoluta do domínio certo, sem a página precisar saber em qual está.
 */
import type { Metadata } from 'next';

import { DEFAULT_SITE, normalizeHost, SITE_URL, siteOrigin } from '@/lib/site';

export { SITE_URL };

/**
 * Domínio (site) da requisição atual — o middleware resolve e manda no
 * header `x-site` (hostname sem www, ou o domínio padrão pra IP/localhost/
 * host desconhecido). Usado por `robots.ts`/`sitemap.ts`/`llms.txt`, que
 * ficam fora do segmento `[site]`. Chamar `headers()` torna a rota dinâmica
 * (só essas pagam esse custo).
 */
export async function resolveSite(): Promise<string> {
  try {
    const { headers } = await import('next/headers');
    const h = await headers();
    return normalizeHost(h.get('x-site')) || DEFAULT_SITE;
  } catch {
    /* fora de uma requisição (build estático) — domínio padrão. */
    return DEFAULT_SITE;
  }
}

export async function resolveSiteUrl(): Promise<string> {
  return siteOrigin(await resolveSite());
}

/** Fallback genérico — o nome real vem de `theme.store_name` (admin). */
export const SITE_NAME = 'Loja';

export interface BuildMetadataInput {
  title?: string;
  description?: string;
  /** Caminho relativo (ex.: `/produto/vestido`). Vira canonical absoluto. */
  path?: string;
  images?: string[];
  /** Marca a rota como noindex (carrinho, checkout, minha-conta, busca). */
  noindex?: boolean;
  /** Nome da loja (do tema). Sem ele, usa o genérico. */
  siteName?: string | null;
  /** Título exato (sem " · loja") — ex.: título do site configurado por domínio. */
  absoluteTitle?: string | null;
}

export function buildMetadata(input: BuildMetadataInput = {}): Metadata {
  const { title, description, path = '/', images, noindex } = input;
  // relativo: resolvido contra o `metadataBase` do domínio (layout [site])
  const canonical = path;
  const name = input.siteName?.trim() || SITE_NAME;
  const fullTitle = input.absoluteTitle?.trim() || (title ? `${title} · ${name}` : name);

  return {
    title: { absolute: fullTitle },
    description,
    alternates: { canonical },
    robots: noindex ? { index: false, follow: false } : undefined,
    openGraph: {
      type: 'website',
      siteName: name,
      title: fullTitle,
      description,
      url: canonical,
      images,
    },
    twitter: {
      card: images && images.length > 0 ? 'summary_large_image' : 'summary',
      title: fullTitle,
      description,
      images,
    },
  };
}

/* ------------------------------------------------------------------ JSON-LD */

export type JsonLd = Record<string, unknown> & { '@context': 'https://schema.org' };

export function organizationJsonLd(
  input: { logoUrl?: string; name?: string | null; url?: string } = {},
): JsonLd {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: input.name?.trim() || SITE_NAME,
    url: input.url ?? SITE_URL,
    ...(input.logoUrl ? { logo: input.logoUrl } : {}),
  };
}

export function webSiteJsonLd(name?: string | null, url: string = SITE_URL): JsonLd {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: name?.trim() || SITE_NAME,
    url,
    potentialAction: {
      '@type': 'SearchAction',
      target: `${url}/busca?q={search_term_string}`,
      'query-input': 'required name=search_term_string',
    },
  };
}

export interface BreadcrumbEntry {
  name: string;
  path: string;
}

export function breadcrumbJsonLd(entries: BreadcrumbEntry[], base: string = SITE_URL): JsonLd {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: entries.map((entry, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: entry.name,
      item: new URL(entry.path, base).toString(),
    })),
  };
}

export interface ProductJsonLdInput {
  name: string;
  description?: string;
  sku?: string;
  brand?: string;
  images?: string[];
  priceCents: number;
  currency?: string;
  availability?: 'InStock' | 'OutOfStock' | 'PreOrder';
  url: string;
  color?: string;
  /** schema.org PeopleAudience -- mesmo gênero que vai no feed do Merchant Center */
  gender?: 'male' | 'female' | 'unisex';
  ratingValue?: number;
  ratingCount?: number;
}

export function productJsonLd(input: ProductJsonLdInput): JsonLd {
  const currency = input.currency ?? 'BRL';
  return {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: input.name,
    description: input.description,
    sku: input.sku,
    ...(input.brand ? { brand: { '@type': 'Brand', name: input.brand } } : {}),
    image: input.images,
    ...(input.color ? { color: input.color } : {}),
    ...(input.gender
      ? { audience: { '@type': 'PeopleAudience', suggestedGender: input.gender } }
      : {}),
    offers: {
      '@type': 'Offer',
      priceCurrency: currency,
      price: (input.priceCents / 100).toFixed(2),
      availability: `https://schema.org/${input.availability ?? 'InStock'}`,
      itemCondition: 'https://schema.org/NewCondition',
      url: input.url,
    },
    ...(input.ratingValue && input.ratingCount
      ? {
          aggregateRating: {
            '@type': 'AggregateRating',
            ratingValue: input.ratingValue,
            reviewCount: input.ratingCount,
          },
        }
      : {}),
  };
}

/** Gênero pelo caminho da categoria ("masculino/botas") -- mesma regra do feed. */
export function genderFromCategoryPath(path?: string | null): 'male' | 'female' | undefined {
  const segs = (path ?? '').toLowerCase().split('/');
  const fem = segs.some((s) => ['feminino', 'feminina', 'mulher'].includes(s));
  const masc = segs.some((s) => ['masculino', 'masculina', 'homem'].includes(s));
  if (fem && !masc) return 'female';
  if (masc && !fem) return 'male';
  return undefined;
}

/** String pronta para `<script type="application/ld+json">`. */
export function jsonLdScript(data: JsonLd | JsonLd[]): string {
  return JSON.stringify(data).replace(/</g, '\\u003c');
}
