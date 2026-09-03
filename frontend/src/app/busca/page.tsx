import type { Metadata } from 'next';
import Link from 'next/link';
import { searchProducts } from '@/modules/catalog/api';
import type { ProductListItem } from '@/modules/catalog/types';
import { buildMetadata } from '@/lib/seo';
import { ProductGrid } from '@/components/catalog/product-grid';
import { TrackOnMount } from '@/components/analytics/track-on-mount';
import { itemFromSearchResult } from '@/modules/analytics';

export const dynamic = 'force-dynamic';

type RawSearchParams = Record<string, string | string[] | undefined>;

interface PageProps {
  searchParams: Promise<RawSearchParams>;
}

function firstParam(value: string | string[] | undefined): string {
  return (Array.isArray(value) ? value[0] : value) ?? '';
}

export async function generateMetadata({ searchParams }: PageProps): Promise<Metadata> {
  const q = firstParam((await searchParams).q).trim();
  return buildMetadata({
    title: q ? `Busca: ${q}` : 'Busca',
    description: q ? `Resultados da busca por "${q}".` : 'Busque produtos na loja.',
    path: '/busca',
    noindex: true,
  });
}

export default async function BuscaPage({ searchParams }: PageProps) {
  const q = firstParam((await searchParams).q).trim();
  const results = q ? await searchProducts(q, 20) : [];
  const products = results.filter((r) => r.type === 'product');
  const categories = results.filter((r) => r.type === 'category');
  const searchItems = products
    .slice(0, 10)
    .map((p, i) =>
      itemFromSearchResult(p, {
        index: i,
        list: { id: 'search_results', name: `Busca: ${q}` },
      }),
    );

  return (
    <div className="flex flex-col gap-6">
      {q && (
        <>
          {/* ação: o usuário pesquisou — sem itens (padrão GA4) */}
          <TrackOnMount event="search" dedupeKey={`search:${q}`} searchTerm={q} />
          {/* estado: os resultados foram apresentados (com itens p/ remarketing) */}
          <TrackOnMount
            event="view_search_results"
            dedupeKey={`vsr:${q}`}
            searchTerm={q}
            itemListId="search_results"
            itemListName={`Busca: ${q}`}
            items={searchItems}
          />
        </>
      )}
      <header className="flex flex-col gap-1">
        <h1 className="text-xl font-bold sm:text-2xl">
          {q ? <>Resultados para “{q}”</> : 'Buscar produtos'}
        </h1>
        {q && (
          <p className="text-sm text-text-muted" aria-live="polite">
            {products.length} {products.length === 1 ? 'produto encontrado' : 'produtos encontrados'}
          </p>
        )}
      </header>

      {!q && (
        <p className="text-sm text-text-muted">
          Use o campo de busca no topo da página para encontrar produtos.
        </p>
      )}

      {categories.length > 0 && (
        <section aria-label="Categorias relacionadas" className="flex flex-wrap gap-2">
          {categories.map((category) => (
            <Link
              key={category.id}
              href={category.url}
              className="inline-flex min-h-touch items-center rounded-card border border-surface-border px-3 text-sm hover:border-primary"
            >
              {category.name}
            </Link>
          ))}
        </section>
      )}

      {q && products.length === 0 && (
        <p className="rounded-card border border-dashed border-surface-border p-8 text-center text-sm text-text-muted">
          {categories.length > 0
            ? `Nenhum produto com esse nome. Veja as categorias relacionadas acima.`
            : `Nada encontrado para “${q}”. Tente outro termo (ex.: “tênis”, “masculino”, a marca).`}
        </p>
      )}

      {products.length > 0 && (
        <ProductGrid
          products={products.map(
            (p): ProductListItem => ({
              id: p.id,
              name: p.name,
              slug: p.slug,
              sku_root: p.sku_root ?? null,
              brand: p.brand ?? null,
              price_cents: p.price_cents ?? 0,
              compare_at_price_cents: p.compare_at_price_cents ?? null,
              discount_pct: p.discount_pct ?? null,
              pix_discount_pct: p.pix_discount_pct ?? null,
              installments_max: p.installments_max ?? null,
              in_stock: p.in_stock ?? true,
              is_featured: p.is_featured ?? false,
              primary_image_url: p.primary_image_url ?? p.image_url ?? null,
              hover_image_url: p.hover_image_url ?? null,
              rating_avg: p.rating_avg ?? 0,
              rating_count: p.rating_count ?? 0,
            }),
          )}
          priorityCount={4}
          listId="search_results"
          listName={`Busca: ${q}`}
        />
      )}
    </div>
  );
}
