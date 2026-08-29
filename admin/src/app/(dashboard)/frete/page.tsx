'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox, Select } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { ADMIN_API_BASE_URL } from '@/lib/admin-api-client';
import { formatBRL } from '@/lib/format';
import { configApi, type ShippingConfig, type ShippingQuoteRate } from '@/modules/config/api';

export default function FretePage() {
  const toast = useToast();
  const { data, loading, error, reload, setData } = useResource(() => configApi.getShipping());
  const [draft, setDraft] = useState<ShippingConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [testZip, setTestZip] = useState('');
  const [testResult, setTestResult] = useState<ShippingQuoteRate[] | null>(null);
  const [testing, setTesting] = useState(false);
  const cfg = draft ?? data;

  const set = <K extends keyof ShippingConfig>(k: K, v: ShippingConfig[K]): void => {
    if (!cfg) return;
    setDraft({ ...cfg, [k]: v });
  };
  const setPkg = (k: string, v: string): void => {
    if (!cfg) return;
    setDraft({ ...cfg, default_package: { ...cfg.default_package, [k]: Number(v) || 0 } });
  };

  async function save(): Promise<void> {
    if (!cfg) return;
    setSaving(true);
    const result = await configApi.putShipping(cfg);
    setSaving(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success('Configuração de frete salva.');
    setData(result.data);
    setDraft(null);
  }

  async function runTest(): Promise<void> {
    if (!testZip.trim()) return;
    setTesting(true);
    setTestResult(null);
    const result = await configApi.testQuote(testZip.replace(/\D/g, ''));
    setTesting(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    setTestResult(result.data.rates);
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Frete"
        description="Provedor, credenciais, CEP de origem e pacote padrão. Provedor atual: Melhor Envio."
      />

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        {cfg && (
          <Card variant="outline" className="flex max-w-2xl flex-col gap-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Select
                label="Provedor"
                value={cfg.active_provider}
                options={[{ value: 'melhor_envio', label: 'Melhor Envio' }]}
                onChange={(e) => set('active_provider', e.target.value)}
              />
              <Input
                label="CEP de origem"
                value={cfg.origin_zip}
                onChange={(e) => set('origin_zip', e.target.value)}
              />
              <Input
                label="Token Melhor Envio"
                value={cfg.melhor_envio_token}
                onChange={(e) => set('melhor_envio_token', e.target.value)}
              />
              <Input
                label="Token do webhook"
                value={cfg.webhook_token}
                onChange={(e) => set('webhook_token', e.target.value)}
              />
            </div>
            <Checkbox
              label="Sandbox (Melhor Envio)"
              checked={cfg.melhor_envio_sandbox}
              onChange={(v) => set('melhor_envio_sandbox', v)}
            />
            <fieldset className="grid gap-4 rounded-card border border-surface-border p-3 sm:grid-cols-4">
              <legend className="px-1 text-sm font-medium">Pacote padrão</legend>
              <Input
                label="Peso (g)"
                inputMode="numeric"
                value={String(cfg.default_package.weight_grams ?? '')}
                onChange={(e) => setPkg('weight_grams', e.target.value)}
              />
              <Input
                label="Comp. (mm)"
                inputMode="numeric"
                value={String(cfg.default_package.length_mm ?? '')}
                onChange={(e) => setPkg('length_mm', e.target.value)}
              />
              <Input
                label="Larg. (mm)"
                inputMode="numeric"
                value={String(cfg.default_package.width_mm ?? '')}
                onChange={(e) => setPkg('width_mm', e.target.value)}
              />
              <Input
                label="Alt. (mm)"
                inputMode="numeric"
                value={String(cfg.default_package.height_mm ?? '')}
                onChange={(e) => setPkg('height_mm', e.target.value)}
              />
            </fieldset>

            <p className="rounded-card bg-bg-subtle p-3 text-xs text-text-muted">
              Webhook do provedor:{' '}
              <code>{ADMIN_API_BASE_URL}/api/webhooks/shipping/melhor_envio</code> — atualiza o
              pedido para POSTADO / EM TRÂNSITO / ENTREGUE.
            </p>

            <Button loading={saving} onClick={() => void save()} className="self-start">
              Salvar frete
            </Button>

            <div className="flex flex-col gap-2 border-t border-surface-border pt-4">
              <h3 className="text-sm font-semibold">Testar cotação</h3>
              <div className="flex flex-wrap items-end gap-2">
                <Input
                  label="CEP de destino"
                  value={testZip}
                  onChange={(e) => setTestZip(e.target.value)}
                />
                <Button variant="outline" loading={testing} onClick={() => void runTest()}>
                  Cotar
                </Button>
              </div>
              {testResult && (
                <ul className="flex flex-col gap-1 text-sm">
                  {testResult.length === 0 && (
                    <li className="text-text-muted">Nenhuma tarifa retornada.</li>
                  )}
                  {testResult.map((r, i) => (
                    <li
                      key={i}
                      className="flex justify-between rounded-card bg-bg-subtle px-3 py-1.5"
                    >
                      <span>
                        {r.carrier} · {r.service} ({r.delivery_days} dias)
                      </span>
                      <span className="font-medium">{formatBRL(r.price_cents)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </Card>
        )}
      </AsyncBoundary>
    </div>
  );
}
