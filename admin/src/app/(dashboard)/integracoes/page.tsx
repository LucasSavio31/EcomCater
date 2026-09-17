'use client';

import { PageHeader } from '@/components/page-header';
import { BlingCard } from './_components/bling-card';

/** Integrações com sistemas externos -- hoje só o Bling, mas a tela já é
 * uma lista de cards (`<BlingCard />`, `<OutraIntegracaoCard />`, ...) pra
 * caber novas integrações sem redesenhar nada. */
export default function IntegracoesPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Integrações"
        description="Conecte a loja a sistemas externos. Mais integrações aparecem aqui no futuro."
      />
      <div className="flex flex-col gap-4">
        <BlingCard />
      </div>
    </div>
  );
}
