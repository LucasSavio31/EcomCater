'use client';

import { useEffect, useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox, Select } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { formatBRL } from '@/lib/format';
import { configApi, type ShippingConfig, type ShippingQuoteRate } from '@/modules/config/api';
import { WebhookUrlBox } from '@/components/webhook-url';
import { CurrencyField } from '@/components/currency-field';
import { onlyDigits } from '@/lib/phone';

/** Máscara de CEP BR — 00000-000, limitada a 8 dígitos. */
function maskCep(v: string): string {
  const d = onlyDigits(v).slice(0, 8);
  return d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d;
}

export default function FretePage() {
  const toast = useToast();
  const { data, loading, error, reload, setData } = useResource(() => configApi.getShipping());
  const [draft, setDraft] = useState<ShippingConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [testZip, setTestZip] = useState('');
  const [testResult, setTestResult] = useState<ShippingQuoteRate[] | null>(null);
  const [testing, setTesting] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const cfg = draft ?? data;

  // volta do OAuth do Melhor Envio (?me=connected|error)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const me = params.get('me');
    if (!me) return;
    if (me === 'connected') {
      toast.success('Melhor Envio conectado!');
      reload();
    } else {
      toast.error('Não foi possível conectar ao Melhor Envio. Confira Client ID/Secret e a Redirect URI.');
    }
    params.delete('me');
    const q = params.toString();
    window.history.replaceState({}, '', window.location.pathname + (q ? `?${q}` : ''));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  async function save(): Promise<void> {
    if (!cfg) return;
    setSaving(true);
    // Segredos: só enviar quando o lojista digitou algo — vazio = manter o que já está salvo.
    const { melhor_envio_token, webhook_token, melhor_envio_client_secret, ...rest } = cfg;
    const body = {
      ...rest,
      ...(melhor_envio_token?.trim() ? { melhor_envio_token: melhor_envio_token.trim() } : {}),
      ...(webhook_token?.trim() ? { webhook_token: webhook_token.trim() } : {}),
      ...(melhor_envio_client_secret?.trim()
        ? { melhor_envio_client_secret: melhor_envio_client_secret.trim() }
        : {}),
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

  async function connectMelhorEnvio(): Promise<void> {
    if (!cfg) return;
    if (!cfg.melhor_envio_client_id?.trim() || !(cfg.melhor_envio_client_secret?.trim() || cfg.has_client_secret)) {
      toast.error('Preencha o Client ID e o Client Secret do app Melhor Envio.');
      return;
    }
    setConnecting(true);
    // salva client id/secret antes de redirecionar
    const saved = await configApi.putShipping({
      melhor_envio_client_id: cfg.melhor_envio_client_id.trim(),
      ...(cfg.melhor_envio_client_secret?.trim()
        ? { melhor_envio_client_secret: cfg.melhor_envio_client_secret.trim() }
        : {}),
    });
    if (!saved.ok) {
      setConnecting(false);
      toast.error(saved.error.message);
      return;
    }
    const res = await configApi.melhorEnvioAuthorizeUrl();
    if (!res.ok) {
      setConnecting(false);
      toast.error(res.error.message);
      return;
    }
    window.location.href = res.data.url;
  }

  async function disconnectMelhorEnvio(): Promise<void> {
    const res = await configApi.melhorEnvioDisconnect();
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    toast.success('Desconectado do Melhor Envio.');
    setDraft(null);
    reload();
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
                inputMode="numeric"
                placeholder="00000-000"
                value={maskCep(cfg.origin_zip ?? '')}
                onChange={(e) => set('origin_zip', onlyDigits(e.target.value).slice(0, 8))}
              />
              <Input
                label="CPF do remetente"
                inputMode="numeric"
                placeholder="000.000.000-00"
                hint="Responsável pelo envio no Melhor Envio (obrigatório p/ gerar etiqueta)."
                value={cfg.sender_cpf ?? ''}
                onChange={(e) => set('sender_cpf', onlyDigits(e.target.value).slice(0, 11))}
              />
              <Input
                label="Token do webhook"
                value={cfg.webhook_token ?? ''}
                placeholder="deixe em branco p/ manter"
                onChange={(e) => set('webhook_token', e.target.value)}
              />
            </div>
            <Checkbox
              label="Sandbox (Melhor Envio)"
              checked={cfg.melhor_envio_sandbox}
              onChange={(v) => set('melhor_envio_sandbox', v)}
            />

            <fieldset className="flex flex-col gap-2 rounded-card border border-surface-border p-3">
              <legend className="px-1 text-sm font-medium">Serviços oferecidos ao cliente</legend>
              <p className="text-xs text-text-muted">
                Só os marcados aparecem no carrinho e no checkout. O Melhor Envio pode devolver
                outros (Jadlog, etc.) — são descartados automaticamente.
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
              <legend className="px-1 text-sm font-medium">Impressão de etiquetas</legend>
              <p className="text-xs text-text-muted">
                O botão <b>Baixar etiqueta (PDF)</b> (na tela do pedido) e o <b>Baixar etiquetas
                (PDF)</b> (em massa) geram o PDF aqui mesmo, sem abrir o site do Melhor Envio. As
                opções abaixo definem como o PDF é montado.
              </p>
              <Select
                label="Formato"
                value={cfg.label_format ?? 'termica_10x15'}
                options={[
                  { value: 'termica_10x15', label: 'Etiqueta térmica 10×15 (1 por página)' },
                  { value: 'a4_4up', label: 'A4 — 4 etiquetas por página' },
                ]}
                onChange={(e) =>
                  set('label_format', e.target.value as 'termica_10x15' | 'a4_4up')
                }
              />
              <Checkbox
                label="Incluir a Declaração de Conteúdo (DACE simples) após cada etiqueta"
                checked={!!cfg.print_declaration}
                onChange={(v) => set('print_declaration', v)}
              />
            </fieldset>

            <fieldset className="flex flex-col gap-2 rounded-card border border-surface-border p-3">
              <legend className="px-1 text-sm font-medium">
                Sincronização automática de rastreio
              </legend>
              <p className="text-xs text-text-muted">
                De quanto em quanto tempo a loja consulta a API do Melhor Envio para preencher o
                código de rastreio e avançar o status do pedido (Rastreio disponível → Enviado →
                Entregue). Mínimo 120&nbsp;s. Deixe <b>0</b> para usar o padrão do servidor
                (900&nbsp;s = 15&nbsp;min). Vale sem reiniciar a API.
              </p>
              <Input
                label="Intervalo da rotina (segundos)"
                type="number"
                min={0}
                step={30}
                value={String(cfg.me_poll_interval_seconds ?? 0)}
                onChange={(e) =>
                  set('me_poll_interval_seconds', Math.max(0, Number(onlyDigits(e.target.value)) || 0))
                }
              />
            </fieldset>

            <fieldset className="flex flex-col gap-3 rounded-card border border-surface-border p-3">
              <legend className="px-1 text-sm font-medium">Conexão Melhor Envio</legend>

              <div className="flex flex-wrap items-center gap-2 text-sm">
                {cfg.has_token ? (
                  <>
                    <span className="inline-flex items-center gap-1 rounded-full bg-success/10 px-2 py-0.5 font-medium text-success">
                      ● Conectado
                    </span>
                    {cfg.token_from_env && (
                      <span className="text-text-muted">via arquivo <code>.env</code> do servidor</span>
                    )}
                    {cfg.token_expires_at && (
                      <span className="text-text-muted">
                        expira em {new Date(cfg.token_expires_at).toLocaleDateString('pt-BR')}
                      </span>
                    )}
                  </>
                ) : (
                  <span className="inline-flex items-center gap-1 rounded-full bg-bg-subtle px-2 py-0.5 font-medium text-text-muted">
                    ○ Não conectado
                  </span>
                )}
              </div>

              <Input
                label="Token do Melhor Envio (JWT)"
                hint="Cole o token pessoal do painel do Melhor Envio (Configurações → Tokens). Salvo junto com “Salvar frete”."
                value={cfg.melhor_envio_token ?? ''}
                placeholder={cfg.has_token ? '•••••••• configurado (deixe em branco p/ manter)' : 'eyJ0eXAiOi...'}
                onChange={(e) => set('melhor_envio_token', e.target.value)}
              />
              {cfg.has_token && !cfg.token_from_env && (
                <Button
                  variant="outline"
                  className="self-start"
                  onClick={() => void disconnectMelhorEnvio()}
                >
                  Remover token
                </Button>
              )}
              {cfg.token_from_env && (
                <p className="text-xs text-text-muted">
                  O token está no <code>.env</code> do servidor — remova por lá, não pelo painel.
                </p>
              )}

              <details className="rounded-card bg-bg-subtle p-2 text-xs text-text-muted">
                <summary className="cursor-pointer font-medium">
                  Conectar via app (OAuth) — renova o token automaticamente
                </summary>
                <div className="flex flex-col gap-3 pt-3">
                  <p>
                    Alternativa ao token manual: crie um <b>Aplicativo</b> no painel do Melhor Envio,
                    cadastre a Redirect URI abaixo, cole o Client ID e o Secret e clique em Conectar.
                  </p>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Input
                      label="Client ID"
                      value={cfg.melhor_envio_client_id ?? ''}
                      onChange={(e) => set('melhor_envio_client_id', e.target.value)}
                    />
                    <Input
                      label="Client Secret"
                      value={cfg.melhor_envio_client_secret ?? ''}
                      placeholder={cfg.has_client_secret ? '•••••••• salvo (deixe em branco p/ manter)' : ''}
                      onChange={(e) => set('melhor_envio_client_secret', e.target.value)}
                    />
                  </div>
                  {cfg.oauth_redirect_uri && (
                    <WebhookUrlBox
                      url={cfg.oauth_redirect_uri}
                      note="Redirect URI: cadastre exatamente esta URL no seu app no painel do Melhor Envio."
                    />
                  )}
                  <Button
                    loading={connecting}
                    className="self-start"
                    onClick={() => void connectMelhorEnvio()}
                  >
                    {cfg.has_token ? 'Reconectar via OAuth' : 'Conectar Melhor Envio'}
                  </Button>
                </div>
              </details>
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

            <WebhookUrlBox
              url={cfg.webhook_url}
              note="Já inclui o token do webhook. Atualiza o pedido para POSTADO / EM TRÂNSITO / ENTREGUE. Em produção troque localhost pelo seu domínio."
            />

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
