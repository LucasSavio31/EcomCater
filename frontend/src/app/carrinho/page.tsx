import type { Metadata } from 'next';
import { CartView } from '@/components/cart/cart-view';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  title: 'Carrinho',
  path: '/carrinho',
  noindex: true,
});

export default function CarrinhoPage() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold sm:text-2xl">Meu carrinho</h1>
      <CartView />
    </div>
  );
}
