'use client';

import { Accordion } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { useResource } from '@/lib/use-resource';
import { woocommerceApi } from '@/modules/woocommerce/api';
import { WooCommerceCard } from './_components/woocommerce-card';
import { UpSellerCard } from './_components/upseller-card';

/** Integrações com sistemas externos — UM PAINEL POR DOMÍNIO (multi-domínio).
 * WooCommerce/API: chaves e webhooks próprios de cada domínio (o ERP de cada
 * um só vê os pedidos daquele domínio; produtos/estoque são os mesmos).
 * UP Seller só no domínio principal: o estoque é compartilhado entre os
 * domínios — duas contas sincronizando o mesmo estoque brigariam. */
export default function IntegracoesPage() {
  const { data, loading, error, reload } = useResource(() => woocommerceApi.sites());

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Integrações"
        description="Conecte cada domínio a sistemas externos. Os pedidos de um domínio vão só para as integrações dele."
      />
      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        {data && (
          <Accordion
            multiple
            defaultOpen={data.length === 1 && data[0] ? [data[0].hostname] : []}
            items={data.map((site) => ({
              id: site.hostname,
              title: (
                <span className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold">{site.hostname}</span>
                  {site.is_primary && (
                    <span className="rounded-full bg-blue-600/10 px-2 py-0.5 text-xs font-medium text-blue-600">
                      principal
                    </span>
                  )}
                  {site.status !== 'active' && (
                    <span className="rounded-full bg-warning/10 px-2 py-0.5 text-xs font-medium text-warning">
                      domínio ainda não ativo
                    </span>
                  )}
                </span>
              ),
              content: (
                <div className="flex flex-col gap-4 pt-2 text-text">
                  <WooCommerceCard hostname={site.is_primary ? null : site.hostname} />
                  {site.is_primary ? (
                    <UpSellerCard />
                  ) : (
                    <p className="text-xs text-text-muted">
                      UP Seller fica no domínio principal: o estoque é o mesmo para todos os
                      domínios, então basta uma conta sincronizando.
                    </p>
                  )}
                </div>
              ),
            }))}
          />
        )}
      </AsyncBoundary>
    </div>
  );
}
