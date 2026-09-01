import type { Metadata } from 'next';
import { CartView } from '@/components/cart/cart-view';
import { getTheme } from '@/modules/theme';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  title: 'Carrinho',
  path: '/carrinho',
  noindex: true,
});

export default async function CarrinhoPage() {
  const theme = await getTheme();
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold sm:text-2xl">Meu carrinho</h1>
      <CartView
        reassurance={
          theme.pdp_reassurance_enabled ? theme.pdp_reassurance_items : null
        }
      />
    </div>
  );
}
