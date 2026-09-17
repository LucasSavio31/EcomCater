'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { Select } from '@/components/form-controls';
import { AsyncBoundary } from '@/components/async-boundary';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { ADMIN_API_BASE_URL } from '@/lib/admin-api-client';
import {
  woocommerceApi,
  type WooKeyCreated,
  type WooPermission,
} from '@/modules/woocommerce/api';

const STORE_URL = ADMIN_API_BASE_URL.replace(/\/$/, '');

function CopyRow({ label, value }: { label: string; value: string }) {
  const toast = useToast();
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-semibold uppercase tracking-wide text-text-muted">{label}</span>
      <div className="flex flex-wrap items-center gap-2">
        <code className="min-w-0 flex-1 break-all rounded border border-surface-border bg-surface px-2 py-1 text-xs">
          {value}
        </code>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            void navigator.clipboard.writeText(value);
            toast.success('Copiado.');
          }}
        >
          Copiar
        </Button>
      </div>
    </div>
  );
}

/** A loja responde a REST API do WooCommerce em `/wp-json/wc/v3/...` --
 * qualquer ERP/ferramenta que já tenha um conector "WooCommerce" pronto
 * (Bling, SoftUp, e por aí vai) conecta aqui direto, sem nada sob medida:
 * só a URL da loja + uma chave gerada abaixo. Uma chave por ferramenta
 * (revogar uma não afeta as outras). */
export function WooCommerceCard() {
  const toast = useToast();
  const keysRes = useResource(() => woocommerceApi.listKeys());
  const webhooksRes = useResource(() => woocommerceApi.listWebhooks());
  const [description, setDescription] = useState('');
  const [permission, setPermission] = useState<WooPermission>('read_write');
  const [creating, setCreating] = useState(false);
  const [revoking, setRevoking] = useState<string | null>(null);
  const [confirmRevoke, setConfirmRevoke] = useState<string | null>(null);
  const [justCreated, setJustCreated] = useState<WooKeyCreated | null>(null);

  async function createKey(): Promise<void> {
    if (!description.trim()) {
      toast.error('Dê um nome pra chave (ex.: "Bling", "SoftUp") -- ajuda a identificar de onde vem cada uma.');
      return;
    }
    setCreating(true);
    const res = await woocommerceApi.createKey({ description: description.trim(), permission });
    setCreating(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    setJustCreated(res.data);
    setDescription('');
    keysRes.reload();
  }

  async function revokeKey(id: string): Promise<void> {
    setRevoking(id);
    const res = await woocommerceApi.revokeKey(id);
    setRevoking(null);
    setConfirmRevoke(null);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    toast.success('Chave revogada.');
    keysRes.reload();
  }

  return (
    <Card variant="outline" className="flex flex-col gap-4">
      <div>
        <h2 className="text-base font-semibold">WooCommerce API (Bling, SoftUp, ...)</h2>
        <p className="text-sm text-text-muted">
          A loja responde como um WooCommerce pra integrações -- em qualquer ERP com um conector
          &quot;WooCommerce&quot; pronto (Bling, SoftUp, e outros), cole a URL da loja abaixo e gere
          uma chave dedicada pra ele. Pedido pago dispara webhook na hora; estoque/preço/status que
          o ERP mudar volta pra cá.
        </p>
      </div>

      <CopyRow label="URL da loja (cole no campo de loja WooCommerce do ERP)" value={STORE_URL} />

      <AsyncBoundary loading={keysRes.loading} error={keysRes.error} onRetry={keysRes.reload}>
        <div className="flex flex-col gap-2">
          <span className="text-sm font-semibold">Chaves de API REST</span>
          {(keysRes.data ?? []).length === 0 && (
            <p className="text-sm text-text-muted">Nenhuma chave gerada ainda.</p>
          )}
          {(keysRes.data ?? []).map((k) => (
            <div
              key={k.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-card border border-surface-border p-2"
            >
              <div className="flex flex-col">
                <span className="text-sm font-medium">{k.description || '(sem descrição)'}</span>
                <code className="text-xs text-text-muted">{k.consumer_key}</code>
                <span className="text-xs text-text-muted">
                  {k.permission === 'read_write' ? 'Leitura e escrita' : k.permission === 'write' ? 'Só escrita' : 'Só leitura'}
                  {k.last_used_at ? ` · usada em ${new Date(k.last_used_at).toLocaleString('pt-BR')}` : ' · nunca usada'}
                </span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="text-danger"
                loading={revoking === k.id}
                onClick={() => setConfirmRevoke(k.id)}
              >
                Revogar
              </Button>
            </div>
          ))}

          <div className="flex flex-wrap items-end gap-2 border-t border-surface-border pt-3">
            <Input
              label="Nome da chave"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Bling, SoftUp..."
            />
            <Select
              label="Permissão"
              value={permission}
              onChange={(e) => setPermission(e.target.value as WooPermission)}
              options={[
                { value: 'read_write', label: 'Leitura e escrita' },
                { value: 'read', label: 'Só leitura' },
                { value: 'write', label: 'Só escrita' },
              ]}
            />
            <Button loading={creating} onClick={() => void createKey()}>
              Gerar chave
            </Button>
          </div>
        </div>
      </AsyncBoundary>

      {webhooksRes.data && webhooksRes.data.length > 0 && (
        <div className="flex flex-col gap-2 border-t border-surface-border pt-3">
          <span className="text-sm font-semibold">Webhooks registrados</span>
          {webhooksRes.data.map((w) => (
            <div key={w.id} className="rounded-card border border-surface-border p-2 text-sm">
              <span className="font-medium">{w.topic}</span>
              <span className="text-text-muted"> · {w.status} </span>
              <div className="break-all text-xs text-text-muted">{w.delivery_url}</div>
            </div>
          ))}
        </div>
      )}

      {justCreated && (
        <div className="flex flex-col gap-3 rounded-card border border-warning bg-bg-subtle p-3">
          <p className="text-sm font-semibold text-warning">
            Guarde a chave secreta agora -- ela só aparece esta vez.
          </p>
          <CopyRow label="Consumer Key" value={justCreated.consumer_key} />
          <CopyRow label="Consumer Secret" value={justCreated.consumer_secret} />
          <Button variant="outline" onClick={() => setJustCreated(null)}>
            Já copiei, fechar
          </Button>
        </div>
      )}

      <ConfirmDialog
        open={confirmRevoke !== null}
        title="Revogar chave"
        description="Quem estiver usando essa chave (o ERP correspondente) para de conseguir acessar a loja."
        confirmLabel="Revogar"
        tone="danger"
        loading={revoking !== null}
        onConfirm={() => confirmRevoke && void revokeKey(confirmRevoke)}
        onCancel={() => setConfirmRevoke(null)}
      />
    </Card>
  );
}
