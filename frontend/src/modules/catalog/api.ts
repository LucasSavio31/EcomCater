import { apiFetch } from '@/lib/api-client';
import type {
  CategoryDetail,
  CategoryNode,
  PagedProducts,
  ProductDetail,
  ProductListItem,
  ProductQuery,
  SearchResultItem,
} from './types';

const EMPTY_PAGE: PagedProducts = {
  items: [],
  total: 0,
  page: 1,
  page_size: 24,
  pages: 0,
  facets: { price: { min: 0, max: 0 }, sizes: [], materials: [], colors: [] },
};

/** Vitrine de destaques da home. Degrada para `[]` se a API estiver fora. */
export async function getFeaturedProducts(limit = 12): Promise<ProductListItem[]> {
  const res = await apiFetch<ProductListItem[]>('/api/products/featured', {
    query: { limit },
    next: { tags: ['products'], revalidate: 300 },
  });
  return res.ok ? res.data : [];
}

/** Listagem paginada com filtros/facetas (PLP e /busca). */
export async function getProducts(params: ProductQuery): Promise<PagedProducts> {
  const query: Record<string, string | number | undefined> = {
    category: params.category,
    price_min: params.price_min,
    price_max: params.price_max,
    sort: params.sort,
    page: params.page,
    page_size: params.page_size,
  };
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value));
  }
  for (const size of params.sizes ?? []) search.append('size', size);
  for (const m of params.materials ?? []) search.append('material', m);
  for (const c of params.colors ?? []) search.append('color', c);

  const res = await apiFetch<PagedProducts>(`/api/products?${search.toString()}`, {
    next: { tags: ['products'], revalidate: 120 },
  });
  return res.ok ? res.data : { ...EMPTY_PAGE, page_size: params.page_size ?? 24 };
}

export async function getProduct(slug: string): Promise<ProductDetail | null> {
  const res = await apiFetch<ProductDetail>(`/api/products/${encodeURIComponent(slug)}`, {
    next: { tags: ['products', `product:${slug}`], revalidate: 120 },
  });
  return res.ok ? res.data : null;
}

/** Produtos por lista de ids (favoritos). Isomórfico. Ordem = ordem dos ids. */
export async function getProductsByIds(ids: string[]): Promise<ProductListItem[]> {
  const clean = [...new Set(ids.filter(Boolean))];
  if (clean.length === 0) return [];
  const res = await apiFetch<ProductListItem[]>('/api/products/by-ids', {
    query: { ids: clean.join(',') },
    cache: 'no-store',
  });
  return res.ok ? res.data : [];
}

export async function getCategoryTree(): Promise<CategoryNode[]> {
  const res = await apiFetch<CategoryNode[]>('/api/categories/tree', {
    next: { tags: ['categories'], revalidate: 300 },
  });
  return res.ok ? res.data : [];
}

export async function getCategoryByPath(path: string): Promise<CategoryDetail | null> {
  const res = await apiFetch<CategoryDetail>(
    `/api/categories/by-path/${path.split('/').map(encodeURIComponent).join('/')}`,
    { next: { tags: ['categories', `category:${path}`], revalidate: 300 } },
  );
  return res.ok ? res.data : null;
}

/** Typeahead do header + página de busca completa. Isomórfico (client + server). */
export async function searchProducts(q: string, limit = 8): Promise<SearchResultItem[]> {
  const term = q.trim();
  if (!term) return [];
  const res = await apiFetch<SearchResultItem[]>('/api/products/search', {
    query: { q: term, limit },
  });
  return res.ok ? res.data : [];
}
