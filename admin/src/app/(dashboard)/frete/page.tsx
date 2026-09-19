'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox, Select } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { formatBRL } from '@/lib/format';
import { configApi, type ShippingConfig, type ShippingQuoteRate } from '@/modules/config/api';
import { CurrencyField } from '@/components/currency-field';
import { onlyDigits } from '@/lib/phone';

/** Máscara de CEP BR — 00000-000, limitada a 8 dígitos. */
function maskCep(v: string): string {
  const d = onlyDigits(v).slice(0, 8);
  return d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d;
}

const PROVIDER_LABEL: Record<string, string> = {
  melhor_envio: 'Melhor Envio',
  frenet: 'Frenet',
};

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
    setDraft({ ...cfg, default_package: { ...(cfg.default_package ?? {}), [k]: Number(v) || 0 } });
  };
  const toggleService = (svc: string, on: boolean): void => {
    const cur = new Set(cfg?.allowed_services ?? []);
    if (on) cur.add(svc);
    else cur.delete(svc);
    set('allowed_services', [...cur]);
  };

  const providerOptions = (['melhor_envio', 'frenet'] as const)
    .filter(
      (p) =>
        p === cfg?.active_provider ||
        (p === 'melhor_envio' ? (cfg?.melhor_envio_enabled ?? true) : cfg?.frenet_enabled),
    )
    .map((p) => ({ value: p, label: PROVIDER_LABEL[p] ?? p }));

  const activeProviderHasQuoteToken =
    cfg?.active_provider === 'melhor_envio' ? cfg?.has_token : cfg?.has_frenet_token;

  async function save(): Promise<void> {
    if (!cfg) return;
    setSaving(true);
    // Só os campos genéricos/compartilhados -- credenciais de cada provedor
    // ficam em Provedores de frete.
    const body: Partial<ShippingConfig> = {
      active_provider: cfg.active_provider,
      origin_zip: cfg.origin_zip,
      sender_cpf: cfg.sender_cpf,
      allowed_services: cfg.allowed_services,
      label_format: cfg.label_format,
      print_declaration: cfg.print_declaration,
      me_poll_interval_seconds: cfg.me_poll_interval_seconds,
      frenet_poll_interval_seconds: cfg.frenet_poll_interval_seconds,
      default_package: cfg.default_package,
      free_shipping_all: cfg.free_shipping_all,
      free_shipping_min_cents: cfg.free_shipping_min_cents,
    };
    const result = await configApi.putShipping(body);
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
    const digits = onlyDigits(testZip);
    if (digits.length !== 8) {
      toast.error('Informe um CEP de destino com 8 dígitos.');
      return;
    }
    setTesting(true);
    setTestResult(null);
    const result = await configApi.testQuote(digits);
    setTesting(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    setTestResult(result.data.rates ?? []);
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Frete"
        description="Escolha qual provedor está ativo. Cadastre e conecte cada um em Provedores de frete."
        actions={
          <Link href="/frete/provedores" className="text-sm text-accent hover:underline">
            → Provedores de frete
          </Link>
        }
      />

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        {cfg && (
          <Card variant="outline" className="flex max-w-2xl flex-col gap-4">
            {providerOptions.length === 0 && (
              <p className="rounded-card bg-warning/10 p-2 text-sm text-warning">
                Nenhum provedor ativo ainda — vá em Provedores de frete e ative pelo menos um.
              </p>
            )}
            {providerOptions.length > 0 && !activeProviderHasQuoteToken && (
              <p className="rounded-card bg-warning/10 p-2 text-sm text-warning">
                O provedor ativo ({PROVIDER_LABEL[cfg.active_provider] ?? cfg.active_provider}) não
                tem o token de cotação preenchido — o cálculo de frete no checkout vai falhar até
                você configurar em Provedores de frete (a menos que &ldquo;Frete grátis&rdquo;
                esteja ligado abaixo).
              </p>
            )}
            <div className="grid gap-4 sm:grid-cols-2">
              <Select
                label="Provedor de frete ativo"
                value={cfg.active_provider}
                options={providerOptions}
                onChange={(e) => set('active_provider', e.target.value)}
              />
              <Input
                label="CEP de origem"
                inputMode="numeric"
                placeholder="00000-000"
                value={maskCep(cfg.origin_zip ?? '')}
                onChange={(e) => set('origin_zip', onlyDigits(e.target.value).slice(0, 8))}
              />
              <Input
                label="CPF do remetente"
                inputMode="numeric"
                placeholder="000.000.000-00"
                hint="Responsável pelo envio (obrigatório p/ gerar etiqueta, nos dois provedores)."
                value={cfg.sender_cpf ?? ''}
                onChange={(e) => set('sender_cpf', onlyDigits(e.target.value).slice(0, 11))}
              />
            </div>

            <fieldset className="flex flex-col gap-2 rounded-card border border-surface-border p-3">
              <legend className="px-1 text-sm font-medium">Serviços oferecidos ao cliente</legend>
              <p className="text-xs text-text-muted">
                Só os marcados aparecem no carrinho e no checkout (vale pro provedor que estiver
                ativo). Outros serviços que o provedor devolver (Jadlog, etc.) são descartados
                automaticamente.
              </p>
              <div className="flex flex-wrap gap-6">
                {(['pac', 'sedex'] as const).map((s) => (
                  <Checkbox
                    key={s}
                    label={s.toUpperCase()}
                    checked={(cfg.allowed_services ?? []).includes(s)}
                    onChange={(v) => toggleService(s, v)}
                  />
                ))}
              </div>
              {(cfg.allowed_services ?? []).length === 0 && (
                <p className="text-xs text-danger">
                  Nenhum serviço marcado — o cliente não verá opção de frete.
                </p>
              )}
            </fieldset>

            <fieldset className="flex flex-col gap-2 rounded-card border border-surface-border p-3">
              <legend className="px-1 text-sm font-medium">Impressão de etiquetas (Melhor Envio)</legend>
              <p className="text-xs text-text-muted">
                Vale só pro Melhor Envio — a etiqueta da Frenet já vem pronta em PDF da própria
                Frenet. O botão <b>Baixar etiqueta (PDF)</b> (na tela do pedido) e o <b>Baixar
                etiquetas (PDF)</b> (em massa) montam o PDF do Melhor Envio aqui mesmo, sem abrir o
                site deles.
              </p>
              <Select
                label="Formato"
                value={cfg.label_format ?? 'termica_10x15'}
                options={[
                  { value: 'termica_10x15', label: 'Etiqueta térmica 10×15 (1 por página)' },
                  { value: 'a4_4up', label: 'A4 — 4 etiquetas por página' },
                ]}
                onChange={(e) => set('label_format', e.target.value as 'termica_10x15' | 'a4_4up')}
              />
              <Checkbox
                label="Incluir a Declaração de Conteúdo (DACE simples) após cada etiqueta"
                checked={!!cfg.print_declaration}
                onChange={(v) => set('print_declaration', v)}
              />
            </fieldset>

            <fieldset className="flex flex-col gap-3 rounded-card border border-surface-border p-3">
              <legend className="px-1 text-sm font-medium">Sincronização automática de rastreio</legend>
              <p className="text-xs text-text-muted">
                De quanto em quanto tempo a loja consulta a API de cada provedor para preencher o
                código de rastreio e avançar o status do pedido. Mínimo 120&nbsp;s cada. Deixe{' '}
                <b>0</b> para usar o padrão do servidor (900&nbsp;s = 15&nbsp;min). Vale sem
                reiniciar a API.
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                <Input
                  label="Intervalo Melhor Envio (segundos)"
                  type="number"
                  min={0}
                  step={30}
                  value={String(cfg.me_poll_interval_seconds ?? 0)}
                  onChange={(e) =>
                    set('me_poll_interval_seconds', Math.max(0, Number(onlyDigits(e.target.value)) || 0))
                  }
                />
                <Input
                  label="Intervalo Frenet (segundos)"
                  type="number"
                  min={0}
                  step={30}
                  value={String(cfg.frenet_poll_interval_seconds ?? 0)}
                  onChange={(e) =>
                    set('frenet_poll_interval_seconds', Math.max(0, Number(onlyDigits(e.target.value)) || 0))
                  }
                />
              </div>
            </fieldset>

            <Checkbox
              label="Frete grátis para todos os pedidos"
              hint="O checkout não calcula frete — a entrega fica R$ 0,00 e o cliente segue direto para o pagamento."
              checked={!!cfg.free_shipping_all}
              onChange={(v) => set('free_shipping_all', v)}
            />
            {!cfg.free_shipping_all && (
              <CurrencyField
                label="Frete grátis para pedidos a partir de (R$)"
                hint="Quando o subtotal do pedido atinge este valor, o frete vira R$ 0,00 automaticamente. Deixe vazio para desligar. A tarja superior mostra “Faltam R$ X para o frete grátis” conforme o carrinho."
                cents={cfg.free_shipping_min_cents ?? null}
                onChange={(c) => set('free_shipping_min_cents', c ?? 0)}
              />
            )}
            <fieldset className="grid gap-4 rounded-card border border-surface-border p-3 sm:grid-cols-4">
              <legend className="px-1 text-sm font-medium">Pacote padrão</legend>
              <Input
                label="Peso (g)"
                inputMode="numeric"
                value={String(cfg.default_package?.weight_grams ?? '')}
                onChange={(e) => setPkg('weight_grams', e.target.value)}
              />
              <Input
                label="Comp. (mm)"
                inputMode="numeric"
                value={String(cfg.default_package?.length_mm ?? '')}
                onChange={(e) => setPkg('length_mm', e.target.value)}
              />
              <Input
                label="Larg. (mm)"
                inputMode="numeric"
                value={String(cfg.default_package?.width_mm ?? '')}
                onChange={(e) => setPkg('width_mm', e.target.value)}
              />
              <Input
                label="Alt. (mm)"
                inputMode="numeric"
                value={String(cfg.default_package?.height_mm ?? '')}
                onChange={(e) => setPkg('height_mm', e.target.value)}
              />
            </fieldset>

            <Button loading={saving} onClick={() => void save()} className="self-start">
              Salvar frete
            </Button>

            <div className="flex flex-col gap-2 border-t border-surface-border pt-4">
              <h3 className="text-sm font-semibold">Testar cotação</h3>
              <div className="flex flex-wrap items-end gap-2">
                <Input
                  label="CEP de destino"
                  inputMode="numeric"
                  placeholder="00000-000"
                  value={testZip}
                  onChange={(e) => setTestZip(maskCep(e.target.value))}
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
