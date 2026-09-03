/**
 * Helpers de SEO — esqueleto tipado (Fase 1).
 * A implementação real (metadata por rota, canonical, OG) entra na Fase 3 (F3.9).
 */
import type { Metadata } from 'next';

export const SITE_URL: string =
  process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000';

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
}

export function buildMetadata(input: BuildMetadataInput = {}): Metadata {
  const { title, description, path = '/', images, noindex } = input;
  const canonical = new URL(path, SITE_URL).toString();
  const name = input.siteName?.trim() || SITE_NAME;
  const fullTitle = title ? `${title} · ${name}` : name;

  return {
    metadataBase: new URL(SITE_URL),
    title: fullTitle,
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

export function organizationJsonLd(input: { logoUrl?: string; name?: string | null } = {}): JsonLd {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: input.name?.trim() || SITE_NAME,
    url: SITE_URL,
    ...(input.logoUrl ? { logo: input.logoUrl } : {}),
  };
}

export function webSiteJsonLd(name?: string | null): JsonLd {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: name?.trim() || SITE_NAME,
    url: SITE_URL,
    potentialAction: {
      '@type': 'SearchAction',
      target: `${SITE_URL}/busca?q={search_term_string}`,
      'query-input': 'required name=search_term_string',
    },
  };
}

export interface BreadcrumbEntry {
  name: string;
  path: string;
}

export function breadcrumbJsonLd(entries: BreadcrumbEntry[]): JsonLd {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: entries.map((entry, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: entry.name,
      item: new URL(entry.path, SITE_URL).toString(),
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
    offers: {
      '@type': 'Offer',
      priceCurrency: currency,
      price: (input.priceCents / 100).toFixed(2),
      availability: `https://schema.org/${input.availability ?? 'InStock'}`,
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

/** String pronta para `<script type="application/ld+json">`. */
export function jsonLdScript(data: JsonLd | JsonLd[]): string {
  return JSON.stringify(data).replace(/</g, '\\u003c');
}
