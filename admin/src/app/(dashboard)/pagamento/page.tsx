'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox, Select } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { ADMIN_API_BASE_URL } from '@/lib/admin-api-client';
import { configApi, type PaymentConfig } from '@/modules/config/api';

export default function PagamentoPage() {
  const toast = useToast();
  const { data, loading, error, reload, setData } = useResource(() => configApi.getPayment());
  const [draft, setDraft] = useState<PaymentConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const cfg = draft ?? data;

  const set = <K extends keyof PaymentConfig>(k: K, v: PaymentConfig[K]): void => {
    if (!cfg) return;
    setDraft({ ...cfg, [k]: v });
  };

  async function save(): Promise<void> {
    if (!cfg) return;
    setSaving(true);
    const result = await configApi.putPayment(cfg);
    setSaving(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success('Configuração de pagamento salva.');
    setData(result.data);
    setDraft(null);
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Pagamento"
        description="Provedor, credenciais e métodos aceitos (PIX, cartão, boleto). Provedor atual: AppMax."
      />

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        {cfg && (
          <Card variant="outline" className="flex max-w-2xl flex-col gap-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Select
                label="Provedor ativo"
                value={cfg.active_provider}
                options={[
                  { value: 'appmax', label: 'AppMax' },
                  { value: 'fake', label: 'Fake (testes locais)' },
                ]}
                onChange={(e) =>
                  set('active_provider', e.target.value as PaymentConfig['active_provider'])
                }
              />
              <Input
                label="Máx. de parcelas"
                inputMode="numeric"
                value={String(cfg.max_installments)}
                onChange={(e) => set('max_installments', Number(e.target.value) || 1)}
              />
              <Input
                label="AppMax — access token"
                value={cfg.appmax_access_token}
                onChange={(e) => set('appmax_access_token', e.target.value)}
              />
              <Input
                label="AppMax — webhook secret"
                value={cfg.appmax_webhook_secret}
                onChange={(e) => set('appmax_webhook_secret', e.target.value)}
              />
            </div>
            <Checkbox
              label="Ambiente sandbox (AppMax)"
              checked={cfg.appmax_sandbox}
              onChange={(v) => set('appmax_sandbox', v)}
            />
            <fieldset className="flex flex-wrap gap-4 rounded-card border border-surface-border p-3">
              <legend className="px-1 text-sm font-medium">Métodos habilitados</legend>
              <Checkbox
                label="Cartão de crédito"
                checked={cfg.methods.credit_card}
                onChange={(v) => set('methods', { ...cfg.methods, credit_card: v })}
              />
              <Checkbox
                label="PIX"
                checked={cfg.methods.pix}
                onChange={(v) => set('methods', { ...cfg.methods, pix: v })}
              />
              <Checkbox
                label="Boleto"
                checked={cfg.methods.boleto}
                onChange={(v) => set('methods', { ...cfg.methods, boleto: v })}
              />
            </fieldset>
            <p className="rounded-card bg-bg-subtle p-3 text-xs text-text-muted">
              Webhook do provedor:{' '}
              <code>{ADMIN_API_BASE_URL}/api/webhooks/payment/appmax</code> — atualiza o pedido para
              PAGO / AGUARDANDO PAGAMENTO / CANCELADO.
            </p>
            <Button loading={saving} onClick={() => void save()} className="self-start">
              Salvar pagamento
            </Button>
          </Card>
        )}
      </AsyncBoundary>
    </div>
  );
}
