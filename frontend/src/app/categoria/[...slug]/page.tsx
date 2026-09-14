import type { Metadata } from 'next';
import { Suspense } from 'react';
import { notFound } from 'next/navigation';
import { getCategoryByPath, getCategoryTree, getProducts } from '@/modules/catalog/api';
import { getTheme } from '@/modules/theme';
import type { CategoryDetail, CategoryNode, ProductSort } from '@/modules/catalog/types';
import type { ThemeSettings } from '@/modules/theme';
import { Breadcrumbs, type Crumb } from '@/components/catalog/breadcrumbs';
import { InfiniteProductGrid } from '@/components/catalog/infinite-product-grid';
import { PlpSort } from '@/components/catalog/plp-sort';
import { PlpFilters, PlpFiltersDrawer } from '@/components/catalog/plp-filters';
import { buildMetadata, breadcrumbJsonLd, jsonLdScript } from '@/lib/seo';
import { TrackOnMount } from '@/components/analytics/track-on-mount';
import { itemFromListItem } from '@/modules/analytics';
import { Spinner } from '@ecom/ui';

// A PLP depende de `searchParams` (filtros, ordenação, paginação na URL), então
// NÃO dá pra colocar no Full Route Cache do Next — `generateStaticParams` aqui
// quebra o render com DYNAMIC_SERVER_USAGE. Fica dinâmica mesmo; a velocidade
// vem do cache Redis da API (`/api/products`, `/api/categories`).
export const dynamic = 'force-dynamic';

type RawSearchParams = Record<string, string | string[] | undefined>;

interface PageProps {
  params: Promise<{ slug: string[] }>;
  searchParams: Promise<RawSearchParams>;
}

type Search = ReturnType<typeof parseSearch>;

const VALID_SORTS: ProductSort[] = ['relevancia', 'menor-preco', 'maior-preco', 'lancamentos'];

function parseSearch(raw: RawSearchParams) {
  const first = (v: string | string[] | undefined): string | undefined =>
    Array.isArray(v) ? v[0] : v;
  const asList = (v: string | string[] | undefined) =>
    v ? (Array.isArray(v) ? v : [v]) : [];
  const sizes = asList(raw.size);
  const materials = asList(raw.material);
  const colors = asList(raw.color);
  const sortRaw = first(raw.sort);
  const sort = VALID_SORTS.includes(sortRaw as ProductSort)
    ? (sortRaw as ProductSort)
    : 'relevancia';
  const page = Math.max(1, Number.parseInt(first(raw.page) ?? '1', 10) || 1);
  const priceMin = first(raw.price_min);
  const priceMax = first(raw.price_max);
  return {
    sizes,
    materials,
    colors,
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

function nodeAt(nodes: CategoryNode[], p: string): CategoryNode | null {
  for (const n of nodes) {
    if (n.path === p) return n;
    const found = nodeAt(n.children, p);
    if (found) return found;
  }
  return null;
}

export async function generateMetadata({ params, searchParams }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const path = slug.join('/');
  const { page } = parseSearch(await searchParams);
  const [category, theme] = await Promise.all([getCategoryByPath(path), getTheme()]);
  const suffix = page > 1 ? ` — página ${page}` : '';
  return buildMetadata({
    siteName: theme.store_name,
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

  // Só o essencial pro "shell" da página (título, breadcrumbs, layout dos
  // filtros): tema e árvore de categorias já vêm do cache Redis da API com
  // `revalidate` de 5 minutos — praticamente instantâneo. A busca de produtos
  // (facetas + paginação, a parte cara em SQL) fica numa Suspense boundary
  // própria, então a navegação nunca mais fica presa atrás da query mais
  // lenta: o usuário já vê título/breadcrumbs/filtros e só a grade de
  // produtos mostra um esqueleto até resolver.
  const [category, tree, theme] = await Promise.all([
    getCategoryByPath(path),
    getCategoryTree(),
    getTheme(),
  ]);

  const filterShow = {
    size: theme.filter_size_enabled,
    price: theme.filter_price_enabled,
    category: theme.filter_category_enabled,
    color: theme.filter_color_enabled,
    material: theme.filter_material_enabled,
  };
  const anyFilter =
    filterShow.size ||
    filterShow.price ||
    filterShow.category ||
    filterShow.color ||
    filterShow.material;

  // "filtro de categoria": subcategorias da atual; se não houver, as irmãs.
  const current = nodeAt(tree, path);
  const parentPath = path.includes('/') ? path.slice(0, path.lastIndexOf('/')) : '';
  const siblingSource = current?.children?.length
    ? current.children
    : (parentPath ? nodeAt(tree, parentPath)?.children : tree) ?? tree;
  const categoryLinks = (siblingSource ?? []).map((c) => ({
    name: c.name,
    path: c.path,
    active: c.path === path,
  }));

  const crumbs = findCrumbs(tree, path);
  const title = category?.name ?? path.split('/').pop()?.replace(/-/g, ' ') ?? 'Categoria';

  return (
    <div className="flex flex-col gap-4">
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

      <Suspense fallback={<CategoryResultsSkeleton anyFilter={anyFilter} />}>
        <CategoryResults
          path={path}
          firstSlug={slug[0]}
          search={search}
          theme={theme}
          tree={tree}
          category={category}
          title={title}
          filterShow={filterShow}
          anyFilter={anyFilter}
          categoryLinks={categoryLinks}
        />
      </Suspense>
    </div>
  );
}

interface CategoryResultsProps {
  path: string;
  firstSlug: string | undefined;
  search: Search;
  theme: ThemeSettings;
  tree: CategoryNode[];
  category: CategoryDetail | null;
  title: string;
  filterShow: Record<'size' | 'price' | 'category' | 'color' | 'material', boolean>;
  anyFilter: boolean;
  categoryLinks: { name: string; path: string; active: boolean }[];
}

async function CategoryResults({
  path,
  firstSlug,
  search,
  theme,
  tree,
  category,
  title,
  filterShow,
  anyFilter,
  categoryLinks,
}: CategoryResultsProps) {
  const result = await getProducts({
    category: path,
    sort: search.sort,
    page: search.page,
    page_size: 24,
    sizes: search.sizes,
    materials: search.materials,
    colors: search.colors,
    price_min: search.price_min,
    price_max: search.price_max,
  });

  if (!category && result.total === 0 && tree.length > 0) {
    // Categoria inexistente e sem produtos → 404 (só quando a API respondeu).
    const known = tree.some((n) => n.path === path || n.slug === firstSlug);
    if (!known) notFound();
  }

  return (
    <>
      <TrackOnMount
        event="view_item_list"
        dedupeKey={`${title}:${result.page}`}
        itemListId={`category:${path}`}
        itemListName={title}
        items={result.items
          .slice(0, 20)
          .map((p, i) =>
            itemFromListItem(p, { index: i, list: { id: `category:${path}`, name: title } }),
          )}
      />

      {anyFilter && (
        <div className="flex items-center justify-between gap-3 lg:hidden">
          <PlpFiltersDrawer facets={result.facets} show={filterShow} categoryLinks={categoryLinks} />
        </div>
      )}

      <div className={anyFilter ? 'grid gap-6 lg:grid-cols-[220px_1fr]' : 'flex flex-col gap-4'}>
        {anyFilter && (
          <aside className="hidden lg:block">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-text-muted">
              Filtros
            </h2>
            <PlpFilters facets={result.facets} show={filterShow} categoryLinks={categoryLinks} />
          </aside>
        )}

        <div className="flex flex-col gap-4">
          <PlpSort total={result.total} />
          <InfiniteProductGrid
            initial={result}
            listId={`category:${path}`}
            listName={title}
            buyButtonLabel={
              theme.card_buy_button_enabled ? theme.card_buy_button_label : undefined
            }
            query={{
              category: path,
              sort: search.sort,
              sizes: search.sizes,
              materials: search.materials,
              colors: search.colors,
              price_min: search.price_min,
              price_max: search.price_max,
              page_size: 24,
            }}
          />
        </div>
      </div>
    </>
  );
}

/** Mantém a forma do layout (coluna de filtros + grade) enquanto os produtos carregam. */
function CategoryResultsSkeleton({ anyFilter }: { anyFilter: boolean }) {
  return (
    <div className={anyFilter ? 'grid gap-6 lg:grid-cols-[220px_1fr]' : 'flex flex-col gap-4'}>
      {anyFilter && <aside className="hidden lg:block" aria-hidden="true" />}
      <div className="flex min-h-[40vh] items-center justify-center">
        <Spinner size="lg" label="Carregando produtos…" />
      </div>
    </div>
  );
}
