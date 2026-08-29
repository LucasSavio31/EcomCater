import type { MetadataRoute } from 'next';
import { SITE_URL } from '@/lib/seo';
import { apiFetch } from '@/lib/api-client';
import { KNOWN_PAGE_SLUGS } from '@/modules/content/api';
import type { CategoryNode, PagedProducts } from '@/modules/catalog/types';

export const revalidate = 3600;

function flattenCategories(nodes: CategoryNode[], acc: string[] = []): string[] {
  for (const node of nodes) {
    acc.push(node.path);
    if (node.children.length) flattenCategories(node.children, acc);
  }
  return acc;
}

async function collectProductSlugs(): Promise<string[]> {
  const slugs: string[] = [];
  const MAX_PAGES = 50;
  for (let page = 1; page <= MAX_PAGES; page += 1) {
    const res = await apiFetch<PagedProducts>('/api/products', {
      query: { page, page_size: 60 },
      next: { revalidate: 3600 },
    });
    if (!res.ok || res.data.items.length === 0) break;
    for (const item of res.data.items) slugs.push(item.slug);
    if (page >= res.data.pages) break;
  }
  return slugs;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const entries: MetadataRoute.Sitemap = [
    { url: `${SITE_URL}/`, lastModified: now, changeFrequency: 'daily', priority: 1 },
  ];

  for (const slug of KNOWN_PAGE_SLUGS) {
    entries.push({
      url: `${SITE_URL}/pagina/${slug}`,
      lastModified: now,
      changeFrequency: 'monthly',
      priority: 0.3,
    });
  }

  try {
    const treeRes = await apiFetch<CategoryNode[]>('/api/categories/tree', {
      next: { revalidate: 3600 },
    });
    if (treeRes.ok) {
      for (const path of flattenCategories(treeRes.data)) {
        entries.push({
          url: `${SITE_URL}/categoria/${path}`,
          lastModified: now,
          changeFrequency: 'daily',
          priority: 0.7,
        });
      }
    }

    for (const slug of await collectProductSlugs()) {
      entries.push({
        url: `${SITE_URL}/produto/${slug}`,
        lastModified: now,
        changeFrequency: 'weekly',
        priority: 0.6,
      });
    }
  } catch {
    /* API fora (ex.: durante o build) — devolve só as rotas estáticas. */
  }

  return entries;
}
