'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { Spinner } from '@ecom/ui';
import { ProductGrid } from '@/components/catalog/product-grid';
import { getProductsByIds } from '@/modules/catalog/api';
import { useWishlist } from '@/modules/wishlist/use-wishlist';
import type { ProductListItem } from '@/modules/catalog/types';

/**
 * Lista de favoritos. A fonte é sempre o `localStorage` do navegador
 * (`useWishlist`, fase 3) — vale logado ou não. As rotas `/favoritos` e
 * `/minha-conta/favoritos` só mudam o link de "voltar".
 */
export function FavoritesView({ showAccountLink = false }: { showAccountLink?: boolean }) {
  const { ids, prune } = useWishlist();
  const [products, setProducts] = useState<ProductListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const hydrated = useRef(false);

  // chave estável para só refazer o fetch quando o conjunto muda de fato
  const key = useMemo(() => [...ids].sort().join(','), [ids]);

  useEffect(() => {
    let alive = true;
    const list = key ? key.split(',') : [];
    if (list.length === 0) {
      setProducts([]);
      setLoading(false);
      hydrated.current = true;
      return;
    }
    if (!hydrated.current) setLoading(true);
    void getProductsByIds(list).then((rows) => {
      if (!alive) return;
      setProducts(rows);
      setLoading(false);
      hydrated.current = true;
      // limpa do cache local o que não existe mais (produto arquivado/removido)
      const found = new Set(rows.map((r) => r.id));
      prune(list.filter((id) => !found.has(id)));
    });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-xl font-semibold sm:text-2xl">
          Meus favoritos{products.length > 0 ? ` (${products.length})` : ''}
        </h1>
        <Link
          href={showAccountLink ? '/minha-conta' : '/'}
          className="text-sm text-primary underline"
        >
          {showAccountLink ? '← Minha conta' : '← Continuar comprando'}
        </Link>
      </div>

      {loading ? (
        <p className="flex items-center gap-2 py-16 text-text-muted">
          <Spinner /> Carregando seus favoritos…
        </p>
      ) : products.length === 0 ? (
        <div className="rounded-card border border-dashed border-surface-border p-8 text-center text-sm text-text-muted">
          <p className="mb-3">Você ainda não favoritou nenhum produto.</p>
          <Link href="/" className="text-primary underline">
            Explorar a loja
          </Link>
        </div>
      ) : (
        <ProductGrid products={products} />
      )}
    </div>
  );
}
