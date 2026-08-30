'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { API_BASE_URL } from '@/lib/api-client';
import type { PagedProducts, ProductListItem } from '@/modules/catalog/types';
import { ProductGrid } from './product-grid';

export interface InfiniteQuery {
  category?: string;
  sort?: string;
  sizes?: string[];
  price_min?: number;
  price_max?: number;
  page_size: number;
}

interface Props {
  initial: PagedProducts;
  query: InfiniteQuery;
}

function buildUrl(q: InfiniteQuery, page: number): string {
  const s = new URLSearchParams();
  if (q.category) s.set('category', q.category);
  if (q.sort && q.sort !== 'relevancia') s.set('sort', q.sort);
  if (q.price_min) s.set('price_min', String(q.price_min));
  if (q.price_max) s.set('price_max', String(q.price_max));
  for (const sz of q.sizes ?? []) s.append('size', sz);
  s.set('page', String(page));
  s.set('page_size', String(q.page_size));
  return `${API_BASE_URL}/api/products?${s.toString()}`;
}

/** Grade com rolagem infinita: carrega a próxima página ao chegar perto do fim. */
export function InfiniteProductGrid({ initial, query }: Props) {
  const [items, setItems] = useState<ProductListItem[]>(initial.items);
  const [page, setPage] = useState(initial.page);
  const [pages, setPages] = useState(initial.pages);
  const [loading, setLoading] = useState(false);
  const sentinel = useRef<HTMLDivElement | null>(null);

  // Reset quando os filtros/ordenação mudam (nova navegação server-side).
  useEffect(() => {
    setItems(initial.items);
    setPage(initial.page);
    setPages(initial.pages);
  }, [initial]);

  const loadMore = useCallback(async () => {
    if (loading || page >= pages) return;
    setLoading(true);
    try {
      const res = await fetch(buildUrl(query, page + 1), { headers: { accept: 'application/json' } });
      if (res.ok) {
        const data = (await res.json()) as PagedProducts;
        setItems((prev) => {
          const seen = new Set(prev.map((p) => p.id));
          return [...prev, ...data.items.filter((p) => !seen.has(p.id))];
        });
        setPage(data.page);
        setPages(data.pages);
      }
    } finally {
      setLoading(false);
    }
  }, [loading, page, pages, query]);

  useEffect(() => {
    const el = sentinel.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) void loadMore();
      },
      { rootMargin: '600px 0px' },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [loadMore]);

  return (
    <div className="flex flex-col gap-4">
      <ProductGrid
        products={items}
        priorityCount={4}
        emptyMessage="Nenhum produto encontrado com os filtros selecionados."
      />
      <div ref={sentinel} aria-hidden="true" className="h-1" />
      <p className="py-2 text-center text-sm text-text-muted">
        {loading
          ? 'Carregando…'
          : page < pages
            ? 'Role para ver mais'
            : items.length > 0
              ? 'Você chegou ao fim.'
              : ''}
      </p>
    </div>
  );
}
