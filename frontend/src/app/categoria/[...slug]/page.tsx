import type { Metadata } from 'next';
import { UnderConstruction } from '@/components/under-construction';
import { buildMetadata } from '@/lib/seo';

interface PageProps {
  params: Promise<{ slug: string[] }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const path = `/categoria/${slug.join('/')}`;
  return buildMetadata({ title: 'Categoria', path });
}

export default async function CategoriaPage({ params }: PageProps) {
  const { slug } = await params;
  return (
    <UnderConstruction title="Categoria" phase="Fase 3 (PLP)">
      <p className="text-sm text-text-muted">
        Caminho: <code>{slug.join(' / ')}</code>
      </p>
    </UnderConstruction>
  );
}
