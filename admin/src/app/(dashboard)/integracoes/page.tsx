'use client';

import { PageHeader } from '@/components/page-header';
import { WooCommerceCard } from './_components/woocommerce-card';
import { UpSellerCard } from './_components/upseller-card';

/** Integrações com sistemas externos -- a tela é uma lista de cards
 * (`<WooCommerceCard />`, `<UpSellerCard />`, ...) pra caber novas
 * integrações sem redesenhar nada. */
export default function IntegracoesPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Integrações"
        description="Conecte a loja a sistemas externos. Mais integrações aparecem aqui no futuro."
      />
      <div className="flex flex-col gap-4">
        <WooCommerceCard />
        <UpSellerCard />
      </div>
    </div>
  );
}
