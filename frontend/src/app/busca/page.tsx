import type { Metadata } from 'next';
import Link from 'next/link';
import Image from 'next/image';
import { searchProducts } from '@/modules/catalog/api';
import { resolveMediaUrl } from '@/lib/media';
import { formatBRL } from '@/lib/format';
import { buildMetadata } from '@/lib/seo';
import { TrackOnMount } from '@/components/analytics/track-on-mount';
import { TrackSelectLink } from '@/components/analytics/track-select-link';
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
        <ul className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4 lg:gap-4">
          {products.map((product, i) => {
            const img = resolveMediaUrl(product.image_url);
            return (
              <li key={product.id}>
                <TrackSelectLink
                  href={product.url}
                  listId="search_results"
                  listName={`Busca: ${q}`}
                  index={i}
                  item={itemFromSearchResult(product, {
                    index: i,
                    list: { id: 'search_results', name: `Busca: ${q}` },
                  })}
                  className="group flex h-full flex-col overflow-hidden rounded-card border border-surface-border bg-surface transition hover:shadow-sm"
                >
                  <span className="relative block aspect-[3/4] overflow-hidden bg-bg-subtle">
                    {img ? (
                      <Image
                        src={img}
                        alt={product.name}
                        fill
                        sizes="(min-width: 1024px) 25vw, (min-width: 768px) 33vw, 50vw"
                        priority={i < 4}
                        className="object-cover"
                      />
                    ) : (
                      <span className="flex h-full items-center justify-center text-xs text-text-muted">
                        sem imagem
                      </span>
                    )}
                  </span>
                  <span className="flex flex-1 flex-col gap-1 p-3">
                    <span className="line-clamp-2 text-sm text-text group-hover:underline">
                      {product.name}
                    </span>
                    {typeof product.price_cents === 'number' && (
                      <span className="mt-auto text-base font-semibold">
                        {formatBRL(product.price_cents)}
                      </span>
                    )}
                  </span>
                </TrackSelectLink>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
