import type { Metadata } from 'next';
import { UnderConstruction } from '@/components/under-construction';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  title: 'Meus pedidos',
  path: '/minha-conta/pedidos',
  noindex: true,
});

export default function PedidosPage() {
  return <UnderConstruction title="Meus pedidos" phase="Fase 8" />;
}
