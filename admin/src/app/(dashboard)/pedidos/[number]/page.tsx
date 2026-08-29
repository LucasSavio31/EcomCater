'use client';

import { useCallback, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Badge, Button, Card } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Select, Textarea } from '@/components/form-controls';
import { StatusBadge } from '@/components/status-badge';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { formatBRL, formatDateTime } from '@/lib/format';
import { orderStatusLabel } from '@/components/status-badge';
import { ordersApi } from '@/modules/orders/api';
import { ORDER_TRANSITIONS, type OrderDetail, type OrderStatus } from '@/modules/orders/types';

function Timeline({ events }: { events: OrderDetail['events'] }) {
  if (events.length === 0) return <p className="text-sm text-text-muted">Sem eventos.</p>;
  const sorted = [...events].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );
  return (
    <ol className="flex flex-col gap-0">
      {sorted.map((ev, i) => (
        <li key={i} className="flex gap-3">
          <div className="flex flex-col items-center">
            <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-accent" />
            {i < sorted.length - 1 && <span className="w-px flex-1 bg-surface-border" />}
          </div>
          <div className="flex flex-col gap-0.5 pb-4">
            <span className="text-sm font-medium">
              {ev.type === 'note'
                ? 'Nota interna'
                : ev.to_status
                  ? `Status: ${orderStatusLabel(ev.to_status)}`
                  : ev.type}
            </span>
            {ev.message && <span className="text-sm text-text-muted">{ev.message}</span>}
            <span className="text-xs text-text-muted">
              {formatDateTime(ev.created_at)} · {ev.actor_type}
            </span>
          </div>
        </li>
      ))}
    </ol>
  );
}

export default function PedidoDetalhePage() {
  const params = useParams<{ number: string }>();
  const number = params.number;
  const router = useRouter();
  const toast = useToast();

  const fetcher = useCallback(() => ordersApi.get(number), [number]);
  const { data, loading, error, reload, setData } = useResource<OrderDetail>(fetcher, [number]);

  const [nextStatus, setNextStatus] = useState<OrderStatus | ''>('');
  const [statusMsg, setStatusMsg] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);

  const transitions = data ? ORDER_TRANSITIONS[data.status] : [];

  async function applyStatus(): Promise<void> {
    if (!nextStatus) return;
    setBusy(true);
    const result = await ordersApi.setStatus(number, nextStatus, statusMsg.trim() || undefined);
    setBusy(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success('Status atualizado.');
    setNextStatus('');
    setStatusMsg('');
    setData(result.data);
  }

  async function addNote(): Promise<void> {
    if (!note.trim()) return;
    setBusy(true);
    const result = await ordersApi.addNote(number, note.trim());
    setBusy(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success('Nota adicionada.');
    setNote('');
    setData(result.data);
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={`Pedido ${number}`}
        back={
          <button
            type="button"
            onClick={() => router.push('/pedidos')}
            className="self-start text-sm text-accent hover:underline"
          >
            ← Voltar para pedidos
          </button>
        }
        description={
          data && (
            <span className="inline-flex flex-wrap items-center gap-2">
              <StatusBadge kind="order" value={data.status} />
              <StatusBadge kind="payment" value={data.payment_status} />
              <span className="text-text-muted">{formatDateTime(data.placed_at)}</span>
            </span>
          )
        }
      />

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        {data && (
          <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
            <div className="flex flex-col gap-6">
              <Card variant="outline" className="flex flex-col gap-3">
                <h2 className="text-lg font-semibold">Itens</h2>
                <ul className="flex flex-col divide-y divide-surface-border">
                  {data.items.map((it, i) => (
                    <li key={i} className="flex gap-3 py-3">
                      <span className="h-14 w-14 shrink-0 overflow-hidden rounded-card bg-bg-subtle">
                        {it.image_url && (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={it.image_url} alt="" className="h-full w-full object-cover" />
                        )}
                      </span>
                      <div className="flex flex-1 flex-col">
                        <span className="text-sm font-medium">{it.name}</span>
                        <span className="text-xs text-text-muted">
                          {it.sku}
                          {it.variant_label ? ` · ${it.variant_label}` : ''}
                        </span>
                        <span className="text-xs text-text-muted">
                          {it.quantity} × {formatBRL(it.unit_price_cents)}
                        </span>
                      </div>
                      <span className="text-sm font-medium">{formatBRL(it.total_cents)}</span>
                    </li>
                  ))}
                </ul>
                <dl className="flex flex-col gap-1 border-t border-surface-border pt-3 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-text-muted">Subtotal</dt>
                    <dd>{formatBRL(data.items_total_cents)}</dd>
                  </div>
                  {data.discount_cents > 0 && (
                    <div className="flex justify-between">
                      <dt className="text-text-muted">
                        Desconto {data.coupon_code ? `(${data.coupon_code})` : ''}
                      </dt>
                      <dd>- {formatBRL(data.discount_cents)}</dd>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <dt className="text-text-muted">Frete</dt>
                    <dd>{formatBRL(data.shipping_cents)}</dd>
                  </div>
                  <div className="flex justify-between text-base font-semibold">
                    <dt>Total</dt>
                    <dd>{formatBRL(data.grand_total_cents)}</dd>
                  </div>
                </dl>
              </Card>

              <Card variant="outline" className="flex flex-col gap-2">
                <h2 className="text-lg font-semibold">Entrega</h2>
                {data.shipping_address ? (
                  <address className="not-italic text-sm text-text-muted">
                    {data.shipping_address.recipient_name && (
                      <div className="text-text">{data.shipping_address.recipient_name}</div>
                    )}
                    <div>
                      {data.shipping_address.street}, {data.shipping_address.number}
                      {data.shipping_address.complement ? ` — ${data.shipping_address.complement}` : ''}
                    </div>
                    <div>
                      {data.shipping_address.district} · {data.shipping_address.city}/
                      {data.shipping_address.state}
                    </div>
                    <div>CEP {data.shipping_address.zip}</div>
                  </address>
                ) : (
                  <p className="text-sm text-text-muted">Sem endereço.</p>
                )}
                <p className="text-sm">
                  <span className="text-text-muted">Método: </span>
                  {data.shipping_method ?? '—'}
                  {data.shipping_service ? ` (${data.shipping_service})` : ''}
                </p>
                {data.customer_note && (
                  <p className="rounded-card bg-bg-subtle p-2 text-sm">
                    <span className="text-text-muted">Observação do cliente: </span>
                    {data.customer_note}
                  </p>
                )}
              </Card>

              <Card variant="outline" className="flex flex-col gap-3">
                <h2 className="text-lg font-semibold">Linha do tempo</h2>
                <Timeline events={data.events} />
              </Card>
            </div>

            <div className="flex flex-col gap-6">
              <Card variant="outline" className="flex flex-col gap-3">
                <h2 className="text-lg font-semibold">Cliente</h2>
                <p className="text-sm">{data.email}</p>
                <Badge tone="neutral">Fulfillment: {data.fulfillment_status}</Badge>
              </Card>

              <Card variant="outline" className="flex flex-col gap-3">
                <h2 className="text-lg font-semibold">Mudar status</h2>
                {transitions.length === 0 ? (
                  <p className="text-sm text-text-muted">
                    Nenhuma transição disponível a partir de “{orderStatusLabel(data.status)}”.
                  </p>
                ) : (
                  <>
                    <Select
                      label="Novo status"
                      value={nextStatus}
                      placeholder="Selecione"
                      options={transitions.map((s) => ({ value: s, label: orderStatusLabel(s) }))}
                      onChange={(e) => setNextStatus(e.target.value as OrderStatus | '')}
                    />
                    <Textarea
                      label="Mensagem (opcional)"
                      value={statusMsg}
                      onChange={(e) => setStatusMsg(e.target.value)}
                      rows={2}
                    />
                    <Button loading={busy} disabled={!nextStatus} onClick={() => void applyStatus()}>
                      Aplicar
                    </Button>
                  </>
                )}
              </Card>

              <Card variant="outline" className="flex flex-col gap-3">
                <h2 className="text-lg font-semibold">Nota interna</h2>
                <Textarea
                  label="Nova nota"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  rows={3}
                />
                <Button variant="outline" loading={busy} disabled={!note.trim()} onClick={() => void addNote()}>
                  Adicionar nota
                </Button>
              </Card>
            </div>
          </div>
        )}
      </AsyncBoundary>
    </div>
  );
}
