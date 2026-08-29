'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { analyticsApi, type AnalyticsConfig, type AnalyticsUpdate } from '@/modules/analytics/api';
import { revalidateStore } from '@/lib/revalidate-store';

type Draft = AnalyticsConfig & { meta_capi_access_token?: string };

export default function RastreamentoPage() {
  const toast = useToast();
  const { data, loading, error, reload, setData } = useResource(() => analyticsApi.get());
  const [draft, setDraft] = useState<Draft | null>(null);
  const [saving, setSaving] = useState(false);

  const cfg: Draft | null = draft ?? (data ? { ...data } : null);
  const dirty = draft !== null;
  const set = <K extends keyof Draft>(k: K, v: Draft[K]) => {
    if (!cfg) return;
    setDraft({ ...cfg, [k]: v });
  };

  async function save() {
    if (!cfg) return;
    setSaving(true);
    const body: AnalyticsUpdate = {
      gtm_enabled: cfg.gtm_enabled,
      gtm_container_id: cfg.gtm_container_id,
      ga4_enabled: cfg.ga4_enabled,
      ga4_measurement_id: cfg.ga4_measurement_id,
      google_ads_enabled: cfg.google_ads_enabled,
      google_ads_conversion_id: cfg.google_ads_conversion_id,
      google_ads_purchase_label: cfg.google_ads_purchase_label,
      meta_pixel_enabled: cfg.meta_pixel_enabled,
      meta_pixel_id: cfg.meta_pixel_id,
      meta_capi_enabled: cfg.meta_capi_enabled,
      meta_test_event_code: cfg.meta_test_event_code,
    };
    if (typeof cfg.meta_capi_access_token === 'string') {
      body.meta_capi_access_token = cfg.meta_capi_access_token;
    }
    const res = await analyticsApi.put(body);
    setSaving(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    await revalidateStore('analytics');
    toast.success('Configuração de rastreamento salva e aplicada na loja.');
    setData(res.data);
    setDraft(null);
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Rastreamento e anúncios"
        description="Ative as tags de marketing. Elas entram no <head> de todas as páginas e disparam os eventos padrão de e-commerce (view_item, add_to_cart, begin_checkout, purchase…)."
      />

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        {cfg && (
          <div className="flex max-w-2xl flex-col gap-5">
            {/* GTM */}
            <Card variant="outline" className="flex flex-col gap-3">
              <Checkbox
                label="Google Tag Manager"
                checked={cfg.gtm_enabled}
                onChange={(v) => set('gtm_enabled', v)}
              />
              <Input
                label="ID do contêiner"
                placeholder="GTM-XXXXXXX"
                value={cfg.gtm_container_id ?? ''}
                onChange={(e) => set('gtm_container_id', e.target.value.trim() || null)}
                disabled={!cfg.gtm_enabled}
              />
              <p className="text-xs text-text-muted">
                Se você gerencia GA4 / Ads / Pixel dentro do GTM, pode deixar as opções abaixo
                desligadas. O dataLayer recebe os eventos no schema de e-commerce do GA4.
              </p>
            </Card>

            {/* GA4 */}
            <Card variant="outline" className="flex flex-col gap-3">
              <Checkbox
                label="Google Analytics 4"
                checked={cfg.ga4_enabled}
                onChange={(v) => set('ga4_enabled', v)}
              />
              <Input
                label="ID de métricas"
                placeholder="G-XXXXXXXXXX"
                value={cfg.ga4_measurement_id ?? ''}
                onChange={(e) => set('ga4_measurement_id', e.target.value.trim() || null)}
                disabled={!cfg.ga4_enabled}
              />
            </Card>

            {/* Google Ads */}
            <Card variant="outline" className="flex flex-col gap-3">
              <Checkbox
                label="Google Ads"
                checked={cfg.google_ads_enabled}
                onChange={(v) => set('google_ads_enabled', v)}
              />
              <Input
                label="ID de conversão"
                placeholder="AW-XXXXXXXXX"
                value={cfg.google_ads_conversion_id ?? ''}
                onChange={(e) => set('google_ads_conversion_id', e.target.value.trim() || null)}
                disabled={!cfg.google_ads_enabled}
              />
              <Input
                label="Rótulo de conversão de compra (opcional)"
                placeholder="AbC-D_efG-h12_34-567"
                value={cfg.google_ads_purchase_label ?? ''}
                onChange={(e) => set('google_ads_purchase_label', e.target.value.trim() || null)}
                disabled={!cfg.google_ads_enabled}
                hint="Usado no evento 'conversion' disparado na página de obrigado."
              />
            </Card>

            {/* Meta Pixel */}
            <Card variant="outline" className="flex flex-col gap-3">
              <Checkbox
                label="Meta Pixel (Facebook / Instagram)"
                checked={cfg.meta_pixel_enabled}
                onChange={(v) => set('meta_pixel_enabled', v)}
              />
              <Input
                label="ID do Pixel"
                placeholder="1234567890123456"
                value={cfg.meta_pixel_id ?? ''}
                onChange={(e) => set('meta_pixel_id', e.target.value.replace(/\D/g, '') || null)}
                disabled={!cfg.meta_pixel_enabled}
              />
            </Card>

            {/* Meta CAPI */}
            <Card variant="outline" className="flex flex-col gap-3">
              <Checkbox
                label="API de Conversões da Meta (server-side)"
                checked={cfg.meta_capi_enabled}
                onChange={(v) => set('meta_capi_enabled', v)}
              />
              <p className="text-xs text-text-muted">
                Envia o evento <strong>Purchase</strong> pelo servidor quando o pedido é pago, com o
                mesmo <code>event_id</code> do Pixel — a Meta deduplica. Requer o ID do Pixel acima.
              </p>
              <label className="flex flex-col gap-1 text-sm font-medium text-text">
                Token da API de Conversões
                <textarea
                  rows={3}
                  className="rounded-card border border-surface-border bg-surface p-2 font-mono text-xs"
                  placeholder={
                    cfg.meta_capi_token_set
                      ? '•••••••••• (token salvo — preencha para substituir)'
                      : 'Cole aqui o token gerado no Gerenciador de Eventos da Meta'
                  }
                  value={cfg.meta_capi_access_token ?? ''}
                  onChange={(e) => set('meta_capi_access_token', e.target.value)}
                  disabled={!cfg.meta_capi_enabled && !cfg.meta_capi_token_set}
                />
              </label>
              {cfg.meta_capi_token_set && (
                <button
                  type="button"
                  className="w-fit text-xs text-text-muted underline"
                  onClick={() => set('meta_capi_access_token', '')}
                >
                  Remover token salvo
                </button>
              )}
              <Input
                label="Código de evento de teste (opcional)"
                placeholder="TEST12345"
                value={cfg.meta_test_event_code ?? ''}
                onChange={(e) => set('meta_test_event_code', e.target.value.trim() || null)}
                hint="Enquanto preenchido, os eventos aparecem na aba 'Testar eventos' da Meta."
              />
            </Card>

            <div className="flex items-center gap-3">
              <Button loading={saving} onClick={() => void save()}>
                Salvar
              </Button>
              {dirty && (
                <button
                  type="button"
                  className="text-sm text-text-muted underline"
                  onClick={() => setDraft(null)}
                >
                  Descartar alterações
                </button>
              )}
            </div>
          </div>
        )}
      </AsyncBoundary>
    </div>
  );
}
