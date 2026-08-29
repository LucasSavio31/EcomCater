import type { Metadata } from 'next';
import { UnderConstruction } from '@/components/under-construction';
import { buildMetadata } from '@/lib/seo';

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  return buildMetadata({ title: 'Produto', path: `/produto/${slug}` });
}

export default async function ProdutoPage({ params }: PageProps) {
  const { slug } = await params;
  return (
    <UnderConstruction title="Produto" phase="Fase 3 (PDP)">
      <p className="text-sm text-text-muted">
        Slug: <code>{slug}</code>
      </p>
    </UnderConstruction>
  );
}
