'use client';

import { adminFetch, ADMIN_API_BASE_URL, type ApiResult } from '@/lib/admin-api-client';
import { getSession } from '@/lib/auth-storage';
import type {
  Category,
  CategoryInput,
  CategoryTreeNode,
  OptionType,
  Paginated,
  ProductDetail,
  ProductInput,
  ProductListItem,
  ProductReview,
  ProductSpec,
  ProductStatus,
  Variant,
  VariantInput,
} from './types';

/** Upload multipart autenticado (o adminFetch força JSON; aqui precisamos de FormData cru). */
async function uploadMultipart<T>(path: string, form: FormData): Promise<ApiResult<T>> {
  const session = getSession();
  try {
    const res = await fetch(`${ADMIN_API_BASE_URL}${path}`, {
      method: 'POST',
      headers: session ? { authorization: `Bearer ${session.accessToken}` } : undefined,
      body: form,
    });
    const text = await res.text();
    const parsed: unknown = text ? JSON.parse(text) : null;
    if (!res.ok) {
      const env = (parsed ?? {}) as { error?: { message?: string }; detail?: string };
      return {
        ok: false,
        error: {
          code: 'upload_error',
          message: env.error?.message ?? env.detail ?? 'Falha no upload',
          status: res.status,
        },
      };
    }
    return { ok: true, data: parsed as T, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: { code: 'network_error', message: err instanceof Error ? err.message : 'Falha de rede', status: 0 },
    };
  }
}

/* ------------------------------ Categorias ------------------------------ */

export const categoriesApi = {
  list: () => adminFetch<Category[]>('/api/admin/categories'),
  tree: () => adminFetch<CategoryTreeNode[]>('/api/admin/categories/tree'),
  get: (id: string) => adminFetch<Category>(`/api/admin/categories/${id}`),
  create: (body: CategoryInput) => adminFetch<Category>('/api/admin/categories', { method: 'POST', body }),
  update: (id: string, body: Partial<CategoryInput>) =>
    adminFetch<Category>(`/api/admin/categories/${id}`, { method: 'PATCH', body }),
  remove: (id: string) => adminFetch<void>(`/api/admin/categories/${id}`, { method: 'DELETE' }),
  reorder: (items: Array<{ id: string; position: number; parent_id?: string | null }>) =>
    adminFetch<void>('/api/admin/categories/reorder', { method: 'POST', body: { items } }),
  uploadImage: (id: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return uploadMultipart<Category>(`/api/admin/categories/${id}/image`, form);
  },
};

/* ------------------------------- Produtos ------------------------------- */

export interface ProductListQuery {
  q?: string;
  status?: ProductStatus | '';
  page?: number;
  page_size?: number;
}

export const productsApi = {
  list: (query: ProductListQuery) =>
    adminFetch<Paginated<ProductListItem>>('/api/admin/products', {
      query: {
        q: query.q || undefined,
        status: query.status || undefined,
        page: query.page ?? 1,
        page_size: query.page_size ?? 20,
      },
    }),
  get: (id: string) => adminFetch<ProductDetail>(`/api/admin/products/${id}`),
  create: (body: ProductInput) => adminFetch<ProductDetail>('/api/admin/products', { method: 'POST', body }),
  update: (id: string, body: Partial<ProductInput>) =>
    adminFetch<ProductDetail>(`/api/admin/products/${id}`, { method: 'PATCH', body }),
  setStatus: (id: string, value: ProductStatus) =>
    adminFetch<ProductDetail>(`/api/admin/products/${id}/status`, { method: 'POST', query: { value } }),
  remove: (id: string) => adminFetch<void>(`/api/admin/products/${id}`, { method: 'DELETE' }),

  putOptionTypes: (id: string, body: OptionType[]) =>
    adminFetch<OptionType[]>(`/api/admin/products/${id}/option-types`, { method: 'PUT', body }),

  createVariant: (id: string, body: VariantInput) =>
    adminFetch<Variant>(`/api/admin/products/${id}/variants`, { method: 'POST', body }),
  updateVariant: (id: string, vid: string, body: Partial<VariantInput>) =>
    adminFetch<Variant>(`/api/admin/products/${id}/variants/${vid}`, { method: 'PATCH', body }),
  deleteVariant: (id: string, vid: string) =>
    adminFetch<void>(`/api/admin/products/${id}/variants/${vid}`, { method: 'DELETE' }),

  uploadImage: (id: string, file: File, variantId?: string, alt?: string) => {
    const form = new FormData();
    form.append('file', file);
    if (variantId) form.append('variant_id', variantId);
    if (alt) form.append('alt', alt);
    return uploadMultipart<{ id: string; url: string }>(`/api/admin/products/${id}/images`, form);
  },
  deleteImage: (id: string, imgId: string) =>
    adminFetch<void>(`/api/admin/products/${id}/images/${imgId}`, { method: 'DELETE' }),
  reorderImages: (id: string, orderedIds: string[], primaryId?: string) =>
    adminFetch<void>(`/api/admin/products/${id}/images/reorder`, {
      method: 'POST',
      body: { ordered_ids: orderedIds, primary_id: primaryId },
    }),

  putSpecs: (id: string, body: ProductSpec[]) =>
    adminFetch<ProductSpec[]>(`/api/admin/products/${id}/specs`, { method: 'PUT', body }),

  reviews: (id: string, status?: string) =>
    adminFetch<ProductReview[]>(`/api/admin/products/${id}/reviews`, {
      query: { status: status || undefined },
    }),
  moderateReview: (id: string, rid: string, status: 'approved' | 'rejected' | 'pending') =>
    adminFetch<ProductReview>(`/api/admin/products/${id}/reviews/${rid}/moderate`, {
      method: 'POST',
      body: { status },
    }),
};
