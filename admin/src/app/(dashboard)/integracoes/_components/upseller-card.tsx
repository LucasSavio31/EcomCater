'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { Checkbox } from '@/components/form-controls';
import { AsyncBoundary } from '@/components/async-boundary';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { upsellerApi, type UpSellerTestResult } from '@/modules/upseller/api';

function StatusPill({ connected }: { connected: boolean }) {
  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-xs font-medium ${
        connected ? 'border-success text-success' : 'border-text-muted text-text-muted'
      }`}
    >
      {connected ? 'Conectado' : 'Não conectado'}
    </span>
  );
}

/** UP Seller: só existe API pública deles pra LER estoque por armazém --
 * sem pedidos, sem produtos. A loja consulta e aplica o total (somado
 * entre armazéns) no SKU que bater exatamente. Uma via só. */
export function UpSellerCard() {
  const toast = useToast();
  const stateRes = useResource(() => upsellerApi.getState());
  const [clientId, setClientId] = useState('');
  const [apiToken, setApiToken] = useState('');
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [testResult, setTestResult] = useState<UpSellerTestResult | null>(null);

  async function save(): Promise<void> {
    if (!clientId.trim() && !apiToken.trim()) {
      toast.error('Preencha o Client ID e o API Token.');
      return;
    }
    setSaving(true);
    const res = await upsellerApi.saveCredentials({
      ...(clientId.trim() ? { client_id: clientId.trim() } : {}),
      ...(apiToken.trim() ? { api_token: apiToken.trim() } : {}),
    });
    setSaving(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    toast.success('Credenciais salvas.');
    setApiToken('');
    stateRes.setData(res.data);
  }

  async function runTest(): Promise<void> {
    setTesting(true);
    setTestResult(null);
    const res = await upsellerApi.testConnection();
    setTesting(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    setTestResult(res.data);
  }

  async function syncNow(): Promise<void> {
    setSyncing(true);
    const res = await upsellerApi.syncNow();
    setSyncing(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    toast.success(`${res.data.variants_updated} variante(s) atualizada(s) de ${res.data.skus_found} SKU(s).`);
    stateRes.reload();
  }

  async function toggleAuto(value: boolean): Promise<void> {
    const res = await upsellerApi.saveToggles({ stock_sync_enabled: value });
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    stateRes.setData(res.data);
  }

  return (
    <Card variant="outline" className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold">UP Seller</h2>
          <p className="text-sm text-text-muted">
            A API pública deles só permite ler estoque por armazém -- sem pedidos, sem produtos.
            A loja soma o estoque entre os armazéns e aplica no SKU que bater exatamente.
          </p>
        </div>
        {stateRes.data && <StatusPill connected={stateRes.data.connected} />}
      </div>

      <AsyncBoundary loading={stateRes.loading} error={stateRes.error} onRetry={stateRes.reload}>
        {stateRes.data && (
          <>
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Client ID"
                value={clientId}
                onChange={(e) => setClientId(e.target.value)}
                placeholder={stateRes.data.has_client_id ? '•••••••• configurado' : ''}
              />
              <Input
                label="API Token"
                type="password"
                value={apiToken}
                onChange={(e) => setApiToken(e.target.value)}
                placeholder={
                  stateRes.data.has_api_token ? '•••••••• configurado (deixe em branco p/ manter)' : ''
                }
              />
            </div>
            <p className="text-xs text-text-muted">
              Gerados em Plataforma Aberta → API Privada, no painel da UP Seller.
            </p>

            <div className="flex flex-wrap gap-2">
              <Button loading={saving} onClick={() => void save()}>
                Salvar
              </Button>
              {stateRes.data.connected && (
                <>
                  <Button variant="outline" loading={testing} onClick={() => void runTest()}>
                    Testar conexão
                  </Button>
                  <Button variant="outline" loading={syncing} onClick={() => void syncNow()}>
                    Sincronizar estoque agora
                  </Button>
                </>
              )}
            </div>

            {testResult && (
              <p className={`text-sm ${testResult.ok ? 'text-success' : 'text-danger'}`}>
                {testResult.message}
              </p>
            )}

            {stateRes.data.connected && (
              <div className="flex flex-col gap-2 border-t border-surface-border pt-3">
                <Checkbox
                  label="Sincronizar estoque automaticamente (a cada 30 min)"
                  checked={stateRes.data.stock_sync_enabled}
                  onChange={(v) => void toggleAuto(v)}
                />
                {stateRes.data.last_sync_summary && (
                  <span className="text-xs text-text-muted">
                    Última sincronização:{' '}
                    {stateRes.data.last_sync_at
                      ? new Date(stateRes.data.last_sync_at).toLocaleString('pt-BR')
                      : '—'}{' '}
                    · {stateRes.data.last_sync_summary}
                  </span>
                )}
              </div>
            )}
          </>
        )}
      </AsyncBoundary>
    </Card>
  );
}
