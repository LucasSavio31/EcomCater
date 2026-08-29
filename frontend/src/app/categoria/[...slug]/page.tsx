import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getCategoryByPath, getCategoryTree, getProducts } from '@/modules/catalog/api';
import type { CategoryNode, ProductSort } from '@/modules/catalog/types';
import { Breadcrumbs, type Crumb } from '@/components/catalog/breadcrumbs';
import { ProductGrid } from '@/components/catalog/product-grid';
import { Pagination } from '@/components/catalog/pagination';
import { PlpSort } from '@/components/catalog/plp-sort';
import { PlpFilters, PlpFiltersDrawer } from '@/components/catalog/plp-filters';
import { buildMetadata, breadcrumbJsonLd, jsonLdScript } from '@/lib/seo';
import { TrackOnMount } from '@/components/analytics/track-on-mount';

export const dynamic = 'force-dynamic';

type RawSearchParams = Record<string, string | string[] | undefined>;

interface PageProps {
  params: Promise<{ slug: string[] }>;
  searchParams: Promise<RawSearchParams>;
}

const VALID_SORTS: ProductSort[] = ['relevancia', 'menor-preco', 'maior-preco', 'lancamentos'];

function parseSearch(raw: RawSearchParams) {
  const first = (v: string | string[] | undefined): string | undefined =>
    Array.isArray(v) ? v[0] : v;
  const sizes = raw.size ? (Array.isArray(raw.size) ? raw.size : [raw.size]) : [];
  const sortRaw = first(raw.sort);
  const sort = VALID_SORTS.includes(sortRaw as ProductSort)
    ? (sortRaw as ProductSort)
    : 'relevancia';
  const page = Math.max(1, Number.parseInt(first(raw.page) ?? '1', 10) || 1);
  const priceMin = first(raw.price_min);
  const priceMax = first(raw.price_max);
  return {
    sizes,
    sort,
    page,
    price_min: priceMin ? Number.parseInt(priceMin, 10) || undefined : undefined,
    price_max: priceMax ? Number.parseInt(priceMax, 10) || undefined : undefined,
  };
}

function findCrumbs(tree: CategoryNode[], path: string): Crumb[] {
  const segments = path.split('/');
  const crumbs: Crumb[] = [{ name: 'Início', url: '/' }];
  let nodes = tree;
  let acc = '';
  for (const segment of segments) {
    acc = acc ? `${acc}/${segment}` : segment;
    const match = nodes.find((n) => n.slug === segment || n.path === acc);
    if (!match) {
      crumbs.push({ name: segment.replace(/-/g, ' '), url: `/categoria/${acc}` });
      break;
    }
    crumbs.push({ name: match.name, url: `/categoria/${match.path}` });
    nodes = match.children;
  }
  return crumbs;
}

export async function generateMetadata({ params, searchParams }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const path = slug.join('/');
  const { page } = parseSearch(await searchParams);
  const category = await getCategoryByPath(path);
  const suffix = page > 1 ? ` — página ${page}` : '';
  return buildMetadata({
    title: (category?.seo_title || category?.name || 'Categoria') + suffix,
    description:
      category?.seo_description ||
      category?.description ||
      `Confira os produtos da categoria ${category?.name ?? path}.`,
    path: page > 1 ? `/categoria/${path}?page=${page}` : `/categoria/${path}`,
  });
}

export default async function CategoriaPage({ params, searchParams }: PageProps) {
  const { slug } = await params;
  const path = slug.join('/');
  const search = parseSearch(await searchParams);

  const [category, tree, result] = await Promise.all([
    getCategoryByPath(path),
    getCategoryTree(),
    getProducts({
      category: path,
      sort: search.sort,
      page: search.page,
      page_size: 24,
      sizes: search.sizes,
      price_min: search.price_min,
      price_max: search.price_max,
    }),
  ]);

  if (!category && result.total === 0 && tree.length > 0) {
    // Categoria inexistente e sem produtos → 404 (só quando a API respondeu).
    const known = tree.some((n) => n.path === path || n.slug === slug[0]);
    if (!known) notFound();
  }

  const crumbs = findCrumbs(tree, path);
  const title = category?.name ?? path.split('/').pop()?.replace(/-/g, ' ') ?? 'Categoria';

  const baseParams = new URLSearchParams();
  if (search.sort !== 'relevancia') baseParams.set('sort', search.sort);
  for (const size of search.sizes) baseParams.append('size', size);
  if (search.price_min) baseParams.set('price_min', String(search.price_min));
  if (search.price_max) baseParams.set('price_max', String(search.price_max));
  const hrefForPage = (p: number) => {
    const qs = new URLSearchParams(baseParams.toString());
    if (p > 1) qs.set('page', String(p));
    const str = qs.toString();
    return str ? `/categoria/${path}?${str}` : `/categoria/${path}`;
  };

  return (
    <div className="flex flex-col gap-4">
      <TrackOnMount
        event="view_item_list"
        dedupeKey={`${title}:${result.page}`}
        itemListName={title}
        items={result.items.slice(0, 20).map((p) => ({
          id: p.slug,
          name: p.name,
          price: p.price_cents / 100,
        }))}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: jsonLdScript(
            breadcrumbJsonLd(crumbs.map((c) => ({ name: c.name, path: c.url ?? '/' }))),
          ),
        }}
      />

      <Breadcrumbs items={crumbs} />

      <header className="flex flex-col gap-1">
        <h1 className="text-xl font-bold capitalize sm:text-2xl">{title}</h1>
        {category?.description && (
          <p className="max-w-prose text-sm text-text-muted">{category.description}</p>
        )}
      </header>

      <div className="flex items-center justify-between gap-3 lg:hidden">
        <PlpFiltersDrawer facets={result.facets} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <aside className="hidden lg:block">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-text-muted">
            Filtros
          </h2>
          <PlpFilters facets={result.facets} />
        </aside>

        <div className="flex flex-col gap-4">
          <PlpSort total={result.total} />
          <ProductGrid
            products={result.items}
            priorityCount={4}
            emptyMessage="Nenhum produto encontrado com os filtros selecionados."
          />
          <Pagination page={result.page} pages={result.pages} hrefForPage={hrefForPage} />
        </div>
      </div>
    </div>
  );
}
