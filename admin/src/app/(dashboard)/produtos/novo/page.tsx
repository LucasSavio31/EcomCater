'use client';

import { AsyncBoundary } from '@/components/async-boundary';
import { useResource } from '@/lib/use-resource';
import { categoriesApi } from '@/modules/catalog/api';
import { ProductForm } from '../_components/product-form';

export default function NovoProdutoPage() {
  const { data, loading, error, reload } = useResource(() => categoriesApi.list());

  return (
    <AsyncBoundary loading={loading} error={error} onRetry={reload}>
      <ProductForm product={null} categories={data ?? []} onSaved={() => undefined} />
    </AsyncBoundary>
  );
}
