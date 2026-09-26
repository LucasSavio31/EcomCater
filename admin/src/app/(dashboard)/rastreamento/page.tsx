'use client';

import { useState } from 'react';
import { Accordion, Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox, Textarea } from '@/components/form-controls';
import { WebhookUrlBox } from '@/components/webhook-url';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import {
  analyticsApi,
  type AnalyticsConfig,
  type AnalyticsUpdate,
  type TrackingSite,
} from '@/modules/analytics/api';
import { revalidateStore } from '@/lib/revalidate-store';

type Draft = AnalyticsConfig & { meta_capi_access_token?: string; ga4_api_secret?: string };

/**
 * Rastreamento, anúncios, verificação e SEO — UM PAINEL POR DOMÍNIO.
 * Pixel/GTM/GA4/Ads/Merchant são por domínio: cada domínio carrega só as
 * próprias tags, e as ferramentas o enxergam como um site único.
 */
export default function RastreamentoPage() {
  const { data, loading, error, reload } = useResource(() => analyticsApi.sites());

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Rastreamento e anúncios"
        description="Cada domínio conectado em Infraestrutura → Domínios tem as próprias tags, verificações e SEO. As tags entram no <head> só do domínio delas e disparam os eventos padrão de e-commerce (view_item, add_to_cart, begin_checkout, purchase…)."
      />

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        {data && (
          <Accordion
            className="max-w-3xl"
            multiple
            defaultOpen={data.length === 1 && data[0] ? [siteKey(data[0])] : []}
            items={data.map((site) => ({
              id: siteKey(site),
              title: (
                <span className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold">{site.hostname ?? 'Domínio principal'}</span>
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
                  <TagSummary cfg={site.config} />
                </span>
              ),
              content: <SiteForm site={site} onSaved={reload} />,
            }))}
          />
        )}
      </AsyncBoundary>
    </div>
  );
}

function siteKey(site: TrackingSite): string {
  return site.hostname ?? 'principal';
}

function TagSummary({ cfg }: { cfg: AnalyticsConfig }) {
  const on = [
    cfg.gtm_enabled && 'GTM',
    cfg.ga4_enabled && 'GA4',
    cfg.google_ads_enabled && 'Ads',
    cfg.meta_pixel_enabled && 'Pixel',
    cfg.meta_capi_enabled && 'CAPI',
    cfg.merchant_center_enabled && 'Merchant',
  ].filter(Boolean);
  return (
    <span className="text-xs font-normal text-text-muted">
      {on.length ? on.join(' · ') : 'nenhuma tag ativa'}
      {cfg.seo_noindex ? ' · fora do Google (noindex)' : ''}
    </span>
  );
}

function SiteForm({ site, onSaved }: { site: TrackingSite; onSaved: () => void }) {
  const toast = useToast();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [saving, setSaving] = useState(false);
  const cfg: Draft = draft ?? { ...site.config };
  const dirty = draft !== null;
  const editable = site.status === 'active' && !!site.hostname;
  const set = <K extends keyof Draft>(k: K, v: Draft[K]) => setDraft({ ...cfg, [k]: v });

  async function save() {
    if (!site.hostname) return;
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
      merchant_center_enabled: cfg.merchant_center_enabled,
      merchant_center_verification_code: cfg.merchant_center_verification_code,
      seo_title: cfg.seo_title,
      seo_description: cfg.seo_description,
      seo_noindex: cfg.seo_noindex,
    };
    if (typeof cfg.meta_capi_access_token === 'string') {
      body.meta_capi_access_token = cfg.meta_capi_access_token;
    }
    if (typeof cfg.ga4_api_secret === 'string') {
      body.ga4_api_secret = cfg.ga4_api_secret;
    }
    const res = await analyticsApi.putSite(site.hostname, body);
    setSaving(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    await revalidateStore('analytics');
    toast.success(`Configuração de ${site.hostname} salva e aplicada na loja.`);
    setDraft(null);
    onSaved();
  }

  const urls = site.seo_urls;

  return (
    <div className="flex flex-col gap-5 pt-2 text-text">
      {!editable && (
        <p className="rounded-card border border-warning/40 bg-warning/10 p-3 text-sm text-warning">
          Este domínio ainda não está ativo em Infraestrutura → Domínios (DNS/SSL). As
          configurações ficam disponíveis assim que ele ativar.
        </p>
      )}

      <fieldset disabled={!editable} className="flex flex-col gap-5">
        {/* SEO do site neste domínio */}
        <Card variant="outline" className="flex flex-col gap-3">
          <p className="text-sm font-semibold">SEO deste domínio</p>
          <Input
            label="Título do site"
            placeholder="Ex.: Botas e Tênis Masculinos | Minha Loja"
            value={cfg.seo_title ?? ''}
            maxLength={200}
            onChange={(e) => set('seo_title', e.target.value || null)}
            hint="Título da página inicial (e dos compartilhamentos) neste domínio. Vazio = nome da loja."
          />
          <Textarea
            label="Descrição do site"
            rows={3}
            maxLength={320}
            placeholder="Frase que aparece no Google abaixo do título da página inicial."
            value={cfg.seo_description ?? ''}
            onChange={(e) => set('seo_description', e.target.value || null)}
          />
          <Checkbox
            label="Não indexar este domínio no Google (noindex)"
            checked={cfg.seo_noindex}
            onChange={(v) => set('seo_noindex', v)}
            hint="Use se este domínio não deve aparecer nas buscas (ex.: domínio só para campanhas)."
          />
          <div className="flex flex-col gap-2">
            <WebhookUrlBox url={urls.site_url} label="Endereço da loja" />
            <WebhookUrlBox
              url={urls.sitemap_url}
              label="Sitemap — cadastre no Google Search Console deste domínio"
            />
            <WebhookUrlBox url={urls.robots_url} label="robots.txt" />
            <WebhookUrlBox url={urls.llms_url} label="llms.txt (resumo do site para IAs)" />
          </div>
        </Card>

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
          <Input
            label="API secret (Measurement Protocol) — opcional"
            type="password"
            placeholder={
              cfg.ga4_api_secret_set
                ? '•••••••••• (segredo salvo — preencha para substituir)'
                : 'Admin > Fluxos de dados > Measurement Protocol'
            }
            value={cfg.ga4_api_secret ?? ''}
            onChange={(e) => set('ga4_api_secret', e.target.value)}
            disabled={!cfg.ga4_enabled}
            hint="Só usado para enviar o evento 'refund' quando um pedido deste domínio é estornado no painel."
          />
          {cfg.ga4_api_secret_set && (
            <button
              type="button"
              className="self-start text-sm text-danger underline"
              onClick={() => set('ga4_api_secret', '')}
            >
              Remover segredo salvo
            </button>
          )}
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

        {/* Google Merchant Center */}
        <Card variant="outline" className="flex flex-col gap-3">
          <Checkbox
            label="Google Merchant Center"
            checked={cfg.merchant_center_enabled}
            onChange={(v) => set('merchant_center_enabled', v)}
          />
          <Input
            label="Código de verificação"
            placeholder="uu3TmG9kfL5y4JIc2ixj7PE4VDl87lvTtjaHX4a8Qn8"
            value={cfg.merchant_center_verification_code ?? ''}
            onChange={(e) => set('merchant_center_verification_code', e.target.value.trim() || null)}
            disabled={!cfg.merchant_center_enabled}
            hint={'Cole só o valor do content="..." da tag <meta name="google-site-verification"> gerada para ESTE domínio.'}
          />
          <p className="text-xs text-text-muted">
            Entra como meta tag no {'<head>'} só deste domínio, pra comprovar ao Google que você é
            dono dele — cada domínio pode ter a própria conta no Merchant Center.
          </p>
          <WebhookUrlBox
            url={urls.feed_url}
            label="Link do arquivo de produtos deste domínio — cole em Fontes de dados → Inserir um link para o arquivo"
            note="Gerado ao vivo a partir do catálogo, com os links deste domínio."
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
            Envia o evento <strong>Purchase</strong> pelo servidor quando um pedido feito neste
            domínio é pago, com o mesmo <code>event_id</code> do Pixel — a Meta deduplica. Requer o
            ID do Pixel acima.
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
          <Button loading={saving} onClick={() => void save()} disabled={!editable || !dirty}>
            Salvar {site.hostname ?? ''}
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
      </fieldset>
    </div>
  );
}
