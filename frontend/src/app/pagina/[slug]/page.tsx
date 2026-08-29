import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getPage } from '@/modules/content/api';
import { Breadcrumbs } from '@/components/catalog/breadcrumbs';
import { buildMetadata } from '@/lib/seo';

export const dynamic = 'force-dynamic';

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const page = await getPage(slug);
  if (!page) return buildMetadata({ title: 'Página', path: `/pagina/${slug}`, noindex: true });
  return buildMetadata({
    title: page.seo_title || page.title,
    description: page.seo_description || undefined,
    path: `/pagina/${slug}`,
  });
}

export default async function InstitutionalPage({ params }: PageProps) {
  const { slug } = await params;
  const page = await getPage(slug);
  if (!page) notFound();

  return (
    <article className="mx-auto flex max-w-3xl flex-col gap-4">
      <Breadcrumbs items={[{ name: 'Início', url: '/' }, { name: page.title }]} />
      <h1 className="text-2xl font-bold">{page.title}</h1>
      <div
        className="max-w-none text-sm leading-relaxed text-text [&_a]:text-primary [&_a]:underline [&_h2]:mt-6 [&_h2]:text-lg [&_h2]:font-semibold [&_p]:mt-3 [&_ul]:mt-3 [&_ul]:list-disc [&_ul]:pl-5"
        // HTML institucional vindo do admin (conteúdo controlado internamente).
        dangerouslySetInnerHTML={{ __html: page.body }}
      />
    </article>
  );
}
