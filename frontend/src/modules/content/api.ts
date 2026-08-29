import { apiFetch } from '@/lib/api-client';

export interface InstitutionalPage {
  slug: string;
  title: string;
  body: string;
  seo_title: string | null;
  seo_description: string | null;
}

/** Slugs institucionais conhecidos (rodapé / FAQ). */
export const KNOWN_PAGE_SLUGS = [
  'quem-somos',
  'politica-de-privacidade',
  'politica-de-vendas',
  'trocas-e-devolucoes',
  'como-comprar',
  'entregas',
  'fale-conosco',
] as const;

export async function getPage(slug: string): Promise<InstitutionalPage | null> {
  const res = await apiFetch<InstitutionalPage>(
    `/api/theme/pages/${encodeURIComponent(slug)}`,
    { next: { tags: ['pages', `page:${slug}`], revalidate: 600 } },
  );
  return res.ok ? res.data : null;
}
