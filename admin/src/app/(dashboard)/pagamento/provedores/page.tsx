'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Badge, Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox } from '@/components/form-controls';
import { WebhookUrlBox } from '@/components/webhook-url';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { configApi } from '@/modules/config/api';

const PROVIDER_LABEL: Record<string, string> = {
  appmax: 'AppMax',
  fake: 'Fake (testes locais)',
};

export default function ProvedoresPagamentoPage() {
  const toast = useToast();
  const { data, loading, error, reload, setData } = useResource(() => configApi.getPayment());
  const [busySlug, setBusySlug] = useState<string | null>(null);

  // rascunho só dos campos de credencial do AppMax (a senha/token nunca vem
  // preenchida do GET — só `has_token`; o usuário digita de novo só se quiser trocar)
  const [appmaxToken, setAppmaxToken] = useState('');
  const [appmaxSecret, setAppmaxSecret] = useState('');

  async function toggleEnabled(slug: string, enabled: boolean): Promise<void> {
    setBusySlug(slug);
    const res = await configApi.putPaymentProvider(slug, { enabled });
    setBusySlug(null);
    if (!res.ok) return toast.error(res.error.message);
    toast.success(`${PROVIDER_LABEL[slug] ?? slug} ${enabled ? 'ativado' : 'desativado'}.`);
    setData(res.data);
  }

  async function saveAppmaxCredentials(sandbox: boolean): Promise<void> {
    setBusySlug('appmax');
    const config: Record<string, unknown> = { sandbox };
    if (appmaxToken.trim()) config.access_token = appmaxToken.trim();
    if (appmaxSecret.trim()) config.webhook_secret = appmaxSecret.trim();
    const res = await configApi.putPaymentProvider('appmax', { config });
    setBusySlug(null);
    if (!res.ok) return toast.error(res.error.message);
    toast.success('Credenciais do AppMax salvas.');
    setData(res.data);
    setAppmaxToken('');
    setAppmaxSecret('');
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Provedores de pagamento"
        description="Cadastre e ative cada provedor aqui. Depois, em Pagamento, escolha qual provedor atende cartão, PIX e boleto."
        actions={
          <Link href="/pagamento" className="text-sm text-accent hover:underline">
            → Vincular métodos
          </Link>
        }
      />

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        {data && (
          <div className="flex max-w-2xl flex-col gap-4">
            <Card variant="outline" className="flex flex-col gap-4">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold">AppMax</h3>
                  <Badge tone={data.providers.appmax?.enabled ? 'success' : 'neutral'}>
                    {data.providers.appmax?.enabled ? 'Ativo' : 'Inativo'}
                  </Badge>
                </div>
                <Checkbox
                  label="Ativo"
                  checked={data.providers.appmax?.enabled ?? false}
                  onChange={(v) => void toggleEnabled('appmax', v)}
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="Access token"
                  hint={data.providers.appmax?.has_token ? 'Preenchido — digite pra trocar' : 'Não configurado'}
                  value={appmaxToken}
                  onChange={(e) => setAppmaxToken(e.target.value)}
                />
                <Input
                  label="Webhook secret"
                  hint={data.providers.appmax?.has_webhook_secret ? 'Preenchido — digite pra trocar' : 'Não configurado'}
                  value={appmaxSecret}
                  onChange={(e) => setAppmaxSecret(e.target.value)}
                />
              </div>
              <Checkbox
                label="Ambiente sandbox"
                checked={data.providers.appmax?.sandbox ?? true}
                onChange={(v) => void saveAppmaxCredentials(v)}
              />
              <WebhookUrlBox
                url={data.webhook_urls.appmax}
                note="Atualiza o pedido para PAGO / AGUARDANDO PAGAMENTO / CANCELADO."
              />
              <Button
                size="sm"
                loading={busySlug === 'appmax'}
                onClick={() => void saveAppmaxCredentials(data.providers.appmax?.sandbox ?? true)}
                className="self-start"
              >
                Salvar credenciais
              </Button>
            </Card>

            <Card variant="outline" className="flex flex-col gap-3">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold">Fake (testes locais)</h3>
                  <Badge tone={data.providers.fake?.enabled ? 'success' : 'neutral'}>
                    {data.providers.fake?.enabled ? 'Ativo' : 'Inativo'}
                  </Badge>
                </div>
                <Checkbox
                  label="Ativo"
                  checked={data.providers.fake?.enabled ?? false}
                  onChange={(v) => void toggleEnabled('fake', v)}
                />
              </div>
              <p className="text-sm text-text-muted">
                Aprova qualquer cobrança na hora, sem bater em API nenhuma — só pra testar o checkout
                em desenvolvimento. Nunca deixe ativo em produção.
              </p>
            </Card>
          </div>
        )}
      </AsyncBoundary>
    </div>
  );
}
