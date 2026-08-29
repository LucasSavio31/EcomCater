import type { Metadata } from 'next';
import { UnderConstruction } from '@/components/under-construction';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  title: 'Carrinho',
  path: '/carrinho',
  noindex: true,
});

export default function CarrinhoPage() {
  return <UnderConstruction title="Carrinho" phase="Fase 4" />;
}
