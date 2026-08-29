import type { Metadata } from 'next';
import { UnderConstruction } from '@/components/under-construction';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  title: 'Meus endereços',
  path: '/minha-conta/enderecos',
  noindex: true,
});

export default function EnderecosPage() {
  return <UnderConstruction title="Meus endereços" phase="Fase 8" />;
}
