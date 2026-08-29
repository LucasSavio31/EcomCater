import type { Metadata } from 'next';
import { UnderConstruction } from '@/components/under-construction';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  title: 'Checkout',
  path: '/checkout',
  noindex: true,
});

export default function CheckoutPage() {
  return <UnderConstruction title="Checkout" phase="Fase 6" />;
}
