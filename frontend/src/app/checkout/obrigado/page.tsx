import type { Metadata } from 'next';
import { UnderConstruction } from '@/components/under-construction';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  title: 'Pedido recebido',
  path: '/checkout/obrigado',
  noindex: true,
});

export default function CheckoutObrigadoPage() {
  return <UnderConstruction title="Obrigado pela compra" phase="Fase 6 / Fase 7" />;
}
