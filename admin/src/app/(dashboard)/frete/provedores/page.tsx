'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Badge, Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox } from '@/components/form-controls';
import { WebhookUrlBox } from '@/components/webhook-url';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { configApi, type ShippingConfig } from '@/modules/config/api';

export default function ProvedoresFretePage() {
  const toast = useToast();
  const { data, loading, error, reload, setData } = useResource(() => configApi.getShipping());
  const [draft, setDraft] = useState<Partial<ShippingConfig>>({});
  const [savingMe, setSavingMe] = useState(false);
  const [savingFrenet, setSavingFrenet] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const cfg = data ? { ...data, ...draft } : null;

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
    setDraft((d) => ({ ...d, [k]: v }));
  };

  async function saveMelhorEnvio(): Promise<void> {
    if (!cfg) return;
    setSavingMe(true);
    const body: Partial<ShippingConfig> = {
      melhor_envio_sandbox: cfg.melhor_envio_sandbox,
      ...(cfg.webhook_token?.trim() ? { webhook_token: cfg.webhook_token.trim() } : {}),
      ...(cfg.melhor_envio_token?.trim() ? { melhor_envio_token: cfg.melhor_envio_token.trim() } : {}),
    };
    const result = await configApi.putShipping(body);
    setSavingMe(false);
    if (!result.ok) return toast.error(result.error.message);
    toast.success('Credenciais do Melhor Envio salvas.');
    setData(result.data);
    setDraft({});
  }

  async function connectMelhorEnvio(): Promise<void> {
    if (!cfg) return;
    if (!cfg.melhor_envio_client_id?.trim() || !(cfg.melhor_envio_client_secret?.trim() || cfg.has_client_secret)) {
      toast.error('Preencha o Client ID e o Client Secret do app Melhor Envio.');
      return;
    }
    setConnecting(true);
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
    if (!res.ok) return toast.error(res.error.message);
    toast.success('Desconectado do Melhor Envio.');
    setDraft({});
    reload();
  }

  async function saveFrenet(): Promise<void> {
    if (!cfg) return;
    setSavingFrenet(true);
    const body: Partial<ShippingConfig> = {
      ...(cfg.frenet_token?.trim() ? { frenet_token: cfg.frenet_token.trim() } : {}),
      ...(cfg.frenet_partner_token?.trim() ? { frenet_partner_token: cfg.frenet_partner_token.trim() } : {}),
      ...(cfg.frenet_webhook_header_name?.trim()
        ? { frenet_webhook_header_name: cfg.frenet_webhook_header_name.trim() }
        : {}),
      ...(cfg.frenet_webhook_header_value?.trim()
        ? { frenet_webhook_header_value: cfg.frenet_webhook_header_value.trim() }
        : {}),
    };
    const result = await configApi.putShipping(body);
    setSavingFrenet(false);
    if (!result.ok) return toast.error(result.error.message);
    toast.success('Credenciais da Frenet salvas.');
    setData(result.data);
    setDraft({});
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Provedores de frete"
        description="Cadastre as credenciais de cada transportadora aqui. Depois, em Frete, escolha qual está ativa."
        actions={
          <Link href="/frete" className="text-sm text-accent hover:underline">
            → Frete
          </Link>
        }
      />

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        {cfg && (
          <div className="flex max-w-2xl flex-col gap-4">
            <Card variant="outline" className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-sm font-semibold">Melhor Envio</h3>
                <Badge tone={cfg.has_token ? 'success' : 'neutral'}>
                  {cfg.has_token ? 'Conectado' : 'Não conectado'}
                </Badge>
                {cfg.token_from_env && (
                  <span className="text-xs text-text-muted">via .env do servidor</span>
                )}
                {cfg.token_expires_at && (
                  <span className="text-xs text-text-muted">
                    expira em {new Date(cfg.token_expires_at).toLocaleDateString('pt-BR')}
                  </span>
                )}
              </div>

              <Checkbox
                label="Sandbox (Melhor Envio)"
                checked={!!cfg.melhor_envio_sandbox}
                onChange={(v) => set('melhor_envio_sandbox', v)}
              />
              <Input
                label="Token do Melhor Envio (JWT)"
                hint="Cole o token pessoal do painel do Melhor Envio (Configurações → Tokens)."
                value={cfg.melhor_envio_token ?? ''}
                placeholder={cfg.has_token ? '•••••••• configurado (deixe em branco p/ manter)' : 'eyJ0eXAiOi...'}
                onChange={(e) => set('melhor_envio_token', e.target.value)}
              />
              <Input
                label="Token do webhook"
                value={cfg.webhook_token ?? ''}
                placeholder="deixe em branco p/ manter"
                onChange={(e) => set('webhook_token', e.target.value)}
              />
              <WebhookUrlBox
                url={cfg.webhook_url}
                note="Cadastre no painel do Melhor Envio. Atualiza o pedido para POSTADO / EM TRÂNSITO / ENTREGUE."
              />

              <div className="flex flex-wrap gap-2">
                <Button loading={savingMe} onClick={() => void saveMelhorEnvio()} className="self-start">
                  Salvar Melhor Envio
                </Button>
                {cfg.has_token && !cfg.token_from_env && (
                  <Button variant="outline" onClick={() => void disconnectMelhorEnvio()}>
                    Remover token
                  </Button>
                )}
              </div>

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
                  <Button loading={connecting} className="self-start" onClick={() => void connectMelhorEnvio()}>
                    {cfg.has_token ? 'Reconectar via OAuth' : 'Conectar Melhor Envio'}
                  </Button>
                </div>
              </details>
            </Card>

            <Card variant="outline" className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-sm font-semibold">Frenet</h3>
                <Badge tone={cfg.has_frenet_token ? 'success' : 'neutral'}>
                  {cfg.has_frenet_token ? 'Conectado' : 'Não conectado'}
                </Badge>
              </div>
              <Input
                label="Token da Frenet"
                hint="Painel da Frenet → Configurações → Integrações/API."
                value={cfg.frenet_token ?? ''}
                placeholder={cfg.has_frenet_token ? '•••••••• configurado (deixe em branco p/ manter)' : ''}
                onChange={(e) => set('frenet_token', e.target.value)}
              />
              <Input
                label="Token de parceiro (whitelabel)"
                hint="Só necessário pra emitir etiqueta pela API — nem toda conta Frenet tem esse acesso liberado; se faltar, solicite ao suporte comercial da Frenet. Cotação e rastreio funcionam sem ele."
                value={cfg.frenet_partner_token ?? ''}
                placeholder={cfg.has_frenet_partner_token ? '•••••••• configurado (deixe em branco p/ manter)' : ''}
                onChange={(e) => set('frenet_partner_token', e.target.value)}
              />
              <div className="grid gap-3 sm:grid-cols-2">
                <Input
                  label="Nome do header do webhook"
                  hint="Escolha um nome (ex.: X-Loja-Token) e cadastre no painel da Frenet."
                  value={cfg.frenet_webhook_header_name ?? ''}
                  onChange={(e) => set('frenet_webhook_header_name', e.target.value)}
                />
                <Input
                  label="Valor do header do webhook"
                  value={cfg.frenet_webhook_header_value ?? ''}
                  placeholder={cfg.has_frenet_webhook_header_value ? '•••••••• configurado (deixe em branco p/ manter)' : ''}
                  onChange={(e) => set('frenet_webhook_header_value', e.target.value)}
                />
              </div>
              <WebhookUrlBox
                url={cfg.frenet_webhook_url}
                note="Cadastre no painel da Frenet junto com o nome/valor do header acima. Sem assinatura própria — a Frenet só verifica por esse header customizado."
              />
              <Button loading={savingFrenet} onClick={() => void saveFrenet()} className="self-start">
                Salvar Frenet
              </Button>
            </Card>
          </div>
        )}
      </AsyncBoundary>
    </div>
  );
}
