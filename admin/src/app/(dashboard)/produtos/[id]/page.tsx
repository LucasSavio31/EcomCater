'use client';

import { useCallback, useState } from 'react';
import { useParams } from 'next/navigation';
import { AsyncBoundary } from '@/components/async-boundary';
import { useResource } from '@/lib/use-resource';
import { categoriesApi, productsApi } from '@/modules/catalog/api';
import type { ProductDetail } from '@/modules/catalog/types';
import { ProductForm } from '../_components/product-form';

export default function EditarProdutoPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const productFetcher = useCallback(() => productsApi.get(id), [id]);
  const product = useResource<ProductDetail>(productFetcher, [id]);
  const categories = useResource(() => categoriesApi.list());

  const [local, setLocal] = useState<ProductDetail | null>(null);
  const current = local ?? product.data;

  const loading = product.loading || categories.loading;
  const error = product.error ?? categories.error;

  return (
    <AsyncBoundary
      loading={loading}
      error={error}
      onRetry={() => {
        product.reload();
        categories.reload();
      }}
    >
      {current && (
        <ProductForm
          product={current}
          categories={categories.data ?? []}
          onSaved={(p) => setLocal(p)}
        />
      )}
    </AsyncBoundary>
  );
}
