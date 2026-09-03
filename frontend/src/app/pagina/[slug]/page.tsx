import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getPage } from '@/modules/content/api';
import { getTheme } from '@/modules/theme';
import { Breadcrumbs } from '@/components/catalog/breadcrumbs';
import { buildMetadata } from '@/lib/seo';

export const revalidate = 300; // ISR — invalidação por tag no /api/revalidate

// Sem isto, uma rota com segmento dinâmico ([slug]) é renderizada a cada
// request (não entra no cache de rota do Next). Com generateStaticParams —
// mesmo retornando [] — a rota vira ISR: o 1º acesso a cada slug renderiza
// no servidor e fica em cache por `revalidate`; os seguintes vêm do cache.
export function generateStaticParams(): { slug: string }[] {
  return [];
}

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const [page, theme] = await Promise.all([getPage(slug), getTheme()]);
  if (!page) return buildMetadata({ title: 'Página', path: `/pagina/${slug}`, noindex: true });
  return buildMetadata({
    title: page.seo_title || page.title,
    description: page.seo_description || undefined,
    path: `/pagina/${slug}`,
    siteName: theme.store_name,
  });
}

/** Remove um H1/H2 logo no início do corpo quando ele só repete o título da
 * página (evita "Quem Somos" duas vezes seguidas). */
function stripLeadingDuplicateHeading(body: string, title: string): string {
  const norm = (s: string) =>
    s
      .toLowerCase()
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  return body.replace(/^\s*<h[12][^>]*>([\s\S]*?)<\/h[12]>\s*/i, (m, inner) =>
    norm(inner.replace(/<[^>]+>/g, '')) === norm(title) ? '' : m,
  );
}

export default async function InstitutionalPage({ params }: PageProps) {
  const { slug } = await params;
  const page = await getPage(slug);
  if (!page) notFound();

  const body = stripLeadingDuplicateHeading(page.body, page.title);

  return (
    <article className="mx-auto flex max-w-2xl flex-col gap-4">
      <Breadcrumbs items={[{ name: 'Início', url: '/' }, { name: page.title }]} />
      <h1 className="text-2xl font-bold">{page.title}</h1>
      <div
        className="max-w-none text-sm leading-relaxed text-text [&_a]:text-primary [&_a]:underline [&_h2]:mt-6 [&_h2]:text-lg [&_h2]:font-semibold [&_p]:mt-3 [&_ul]:mt-3 [&_ul]:list-disc [&_ul]:pl-5"
        // HTML institucional vindo do admin (conteúdo controlado internamente).
        dangerouslySetInnerHTML={{ __html: body }}
      />
    </article>
  );
}
