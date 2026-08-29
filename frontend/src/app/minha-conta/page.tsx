import type { Metadata } from 'next';
import { UnderConstruction } from '@/components/under-construction';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  title: 'Minha conta',
  path: '/minha-conta',
  noindex: true,
});

export default function MinhaContaPage() {
  return <UnderConstruction title="Minha conta" phase="Fase 8" />;
}
