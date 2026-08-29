import type { Metadata } from 'next';
import { CheckoutView } from '@/components/checkout/checkout-view';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  title: 'Checkout',
  path: '/checkout',
  noindex: true,
});

export default function CheckoutPage() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold sm:text-2xl">Finalizar compra</h1>
      <CheckoutView />
    </div>
  );
}
