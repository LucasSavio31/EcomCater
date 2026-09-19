'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Select } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { configApi } from '@/modules/config/api';

const PROVIDER_LABEL: Record<string, string> = {
  appmax: 'AppMax',
  fake: 'Fake (testes locais)',
};

const METHOD_LABEL: Record<'credit_card' | 'pix' | 'boleto', string> = {
  credit_card: 'Cartão de crédito',
  pix: 'PIX',
  boleto: 'Boleto',
};

export default function PagamentoPage() {
  const toast = useToast();
  const { data, loading, error, reload, setData } = useResource(() => configApi.getPayment());
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [installments, setInstallments] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const methodProviders = { ...(data?.method_providers ?? {}), ...draft };
  const maxInstallments = installments ?? data?.max_installments ?? 12;
  const enabledProviders = Object.entries(data?.providers ?? {}).filter(([, p]) => p.enabled);

  async function save(): Promise<void> {
    setSaving(true);
    const result = await configApi.putPaymentMethodProviders({
      credit_card: methodProviders.credit_card || null,
      pix: methodProviders.pix || null,
      boleto: methodProviders.boleto || null,
      max_installments: maxInstallments,
    });
    setSaving(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success('Vínculo de pagamento salvo.');
    setData(result.data);
    setDraft({});
    setInstallments(null);
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Pagamento"
        description="Escolha qual provedor atende cada método. Cadastre e ative os provedores em Provedores de pagamento."
        actions={
          <Link href="/pagamento/provedores" className="text-sm text-accent hover:underline">
            → Provedores de pagamento
          </Link>
        }
      />

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        {data && (
          <Card variant="outline" className="flex max-w-2xl flex-col gap-4">
            {enabledProviders.length === 0 && (
              <p className="rounded-card bg-warning/10 p-2 text-sm text-warning">
                Nenhum provedor ativo ainda — vá em Provedores de pagamento e ative pelo menos um antes
                de vincular os métodos.
              </p>
            )}
            <div className="grid gap-4 sm:grid-cols-2">
              {(['credit_card', 'pix', 'boleto'] as const).map((method) => (
                <Select
                  key={method}
                  label={METHOD_LABEL[method]}
                  value={methodProviders[method] ?? ''}
                  placeholder="Desligado (nenhum provedor)"
                  options={enabledProviders.map(([slug]) => ({
                    value: slug,
                    label: PROVIDER_LABEL[slug] ?? slug,
                  }))}
                  onChange={(e) => setDraft((d) => ({ ...d, [method]: e.target.value }))}
                />
              ))}
              <Input
                label="Máx. de parcelas"
                inputMode="numeric"
                value={String(maxInstallments)}
                onChange={(e) => setInstallments(Number(e.target.value) || 1)}
              />
            </div>
            <Button loading={saving} onClick={() => void save()} className="self-start">
              Salvar vínculo
            </Button>
          </Card>
        )}
      </AsyncBoundary>
    </div>
  );
}
