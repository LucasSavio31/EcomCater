import type { ProductListItem } from '@/modules/catalog/types';
import { ProductCard } from './product-card';

interface ProductGridProps {
  products: ProductListItem[];
  /** Nº de itens que recebem `priority` (LCP da 1ª dobra). */
  priorityCount?: number;
  emptyMessage?: string;
}

/** Grade responsiva: 2 col mobile / 3 col tablet / 4 col desktop. */
export function ProductGrid({
  products,
  priorityCount = 0,
  emptyMessage = 'Nenhum produto encontrado.',
}: ProductGridProps) {
  if (products.length === 0) {
    return (
      <p className="rounded-card border border-dashed border-surface-border p-8 text-center text-sm text-text-muted">
        {emptyMessage}
      </p>
    );
  }

  return (
    <ul className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4 lg:gap-4">
      {products.map((product, i) => (
        <li key={product.id} className="flex">
          <ProductCard product={product} priority={i < priorityCount} className="w-full" />
        </li>
      ))}
    </ul>
  );
}
