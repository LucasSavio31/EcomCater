'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Badge, Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Select, Textarea } from '@/components/form-controls';
import { StatusBadge, orderStatusLabel } from '@/components/status-badge';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { formatBRL, formatDateTime } from '@/lib/format';
import { ordersApi, type OrderEditPayload } from '@/modules/orders/api';
import { ORDER_TRANSITIONS, type OrderDetail, type OrderStatus } from '@/modules/orders/types';

const ADDR_FIELDS: { key: keyof NonNullable<OrderEditPayload['shipping_address']>; label: string }[] = [
  { key: 'recipient_name', label: 'Destinatário' },
  { key: 'zip', label: 'CEP' },
  { key: 'street', label: 'Rua' },
  { key: 'number', label: 'Número' },
  { key: 'complement', label: 'Complemento' },
  { key: 'district', label: 'Bairro' },
  { key: 'city', label: 'Cidade' },
  { key: 'state', label: 'UF' },
  { key: 'phone', label: 'Telefone' },
];

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
  const [confirmDel, setConfirmDel] = useState(false);

  // Rascunho de edição (cliente + endereço + variação dos itens)
  const [edit, setEdit] = useState<OrderEditPayload>({});
  useEffect(() => {
    if (!data) return;
    setEdit({
      email: data.email,
      shipping_address: { ...(data.shipping_address ?? {}) },
      shipping_service: { tracking_code: '' },
      items: data.items.map((it) => ({
        id: it.id ?? '',
        variant_label: it.variant_label,
        name: it.name,
      })),
    });
  }, [data]);

  const transitions = data ? ORDER_TRANSITIONS[data.status] : [];

  async function applyStatus(): Promise<void> {
    if (!nextStatus) return;
    setBusy(true);
    const result = await ordersApi.setStatus(number, nextStatus, statusMsg.trim() || undefined);
    setBusy(false);
    if (!result.ok) return toast.error(result.error.message);
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
    if (!result.ok) return toast.error(result.error.message);
    toast.success('Nota adicionada.');
    setNote('');
    setData(result.data);
  }

  async function saveEdit(): Promise<void> {
    setBusy(true);
    const payload: OrderEditPayload = {
      email: edit.email,
      shipping_address: edit.shipping_address,
      items: edit.items?.filter((i) => i.id),
    };
    if (edit.shipping_service?.tracking_code?.trim()) {
      payload.shipping_service = { tracking_code: edit.shipping_service.tracking_code.trim() };
    }
    const result = await ordersApi.edit(number, payload);
    setBusy(false);
    if (!result.ok) return toast.error(result.error.message);
    toast.success('Pedido atualizado.');
    setData(result.data);
  }

  async function doDelete(): Promise<void> {
    setBusy(true);
    const result = await ordersApi.remove(number);
    setBusy(false);
    setConfirmDel(false);
    if (!result.ok) return toast.error(result.error.message);
    toast.success('Pedido excluído.');
    router.push('/pedidos');
  }

  const setAddr = (k: string, v: string) =>
    setEdit((e) => ({ ...e, shipping_address: { ...e.shipping_address, [k]: v } }));
  const setItem = (id: string, v: string) =>
    setEdit((e) => ({
      ...e,
      items: e.items?.map((it) => (it.id === id ? { ...it, variant_label: v } : it)),
    }));

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

      {data && (
        <div className="flex flex-wrap gap-2">
          <Link
            href={`/pedidos/imprimir?ids=${number}`}
            target="_blank"
            className="rounded-card border border-surface-border px-3 py-1.5 text-sm hover:border-primary"
          >
            📄 PDF do pedido
          </Link>
          <Link
            href={`/pedidos/etiquetas?ids=${number}`}
            target="_blank"
            className="rounded-card border border-surface-border px-3 py-1.5 text-sm hover:border-primary"
          >
            🏷️ Etiqueta
          </Link>
          <Button size="sm" variant="ghost" className="text-danger" onClick={() => setConfirmDel(true)}>
            Excluir pedido
          </Button>
        </div>
      )}

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        {data && (
          <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
            <div className="flex flex-col gap-6">
              <Card variant="outline" className="flex flex-col gap-3">
                <h2 className="text-lg font-semibold">Itens</h2>
                <ul className="flex flex-col divide-y divide-surface-border">
                  {data.items.map((it, i) => (
                    <li key={it.id ?? i} className="flex gap-3 py-3">
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
                          {it.supplier ? ` · Forn.: ${it.supplier}` : ''}
                        </span>
                        <span className="text-xs text-text-muted">
                          {it.quantity} × {formatBRL(it.unit_price_cents)}
                        </span>
                        {it.id && (
                          <Input
                            className="mt-1"
                            label="Variação (tam./cor)"
                            value={edit.items?.find((x) => x.id === it.id)?.variant_label ?? ''}
                            onChange={(e) => setItem(it.id!, e.target.value)}
                          />
                        )}
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

              <Card variant="outline" className="flex flex-col gap-3">
                <h2 className="text-lg font-semibold">Editar dados de entrega e cliente</h2>
                <Input
                  label="E-mail do cliente"
                  value={edit.email ?? ''}
                  onChange={(e) => setEdit((s) => ({ ...s, email: e.target.value }))}
                />
                <div className="grid gap-3 sm:grid-cols-2">
                  {ADDR_FIELDS.map((f) => (
                    <Input
                      key={f.key}
                      label={f.label}
                      value={(edit.shipping_address?.[f.key] as string) ?? ''}
                      onChange={(e) => setAddr(f.key, e.target.value)}
                    />
                  ))}
                </div>
                <Input
                  label="Código de rastreio (tracking)"
                  value={edit.shipping_service?.tracking_code ?? ''}
                  onChange={(e) =>
                    setEdit((s) => ({ ...s, shipping_service: { tracking_code: e.target.value } }))
                  }
                />
                <Button loading={busy} onClick={() => void saveEdit()}>
                  Salvar alterações
                </Button>
              </Card>

              <Card variant="outline" className="flex flex-col gap-2">
                <h2 className="text-lg font-semibold">Entrega</h2>
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
              <Card variant="outline" className="flex flex-col gap-2">
                <h2 className="text-lg font-semibold">Pagamento</h2>
                {data.payment ? (
                  <dl className="flex flex-col gap-1 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-text-muted">Provedor</dt>
                      <dd>{data.payment.provider}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-text-muted">Método</dt>
                      <dd>{data.payment.method}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-text-muted">Situação</dt>
                      <dd>{data.payment.status}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-text-muted">Valor</dt>
                      <dd>{formatBRL(data.payment.amount_cents)}</dd>
                    </div>
                    {data.payment.installments ? (
                      <div className="flex justify-between">
                        <dt className="text-text-muted">Parcelas</dt>
                        <dd>{data.payment.installments}x</dd>
                      </div>
                    ) : null}
                    {data.payment.paid_at && (
                      <div className="flex justify-between">
                        <dt className="text-text-muted">Pago em</dt>
                        <dd>{formatDateTime(data.payment.paid_at)}</dd>
                      </div>
                    )}
                    {data.payment.provider_charge_id && (
                      <div className="flex justify-between">
                        <dt className="text-text-muted">ID cobrança</dt>
                        <dd className="truncate">{data.payment.provider_charge_id}</dd>
                      </div>
                    )}
                    {data.payment.boleto_url && (
                      <a
                        href={data.payment.boleto_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-accent hover:underline"
                      >
                        Ver boleto
                      </a>
                    )}
                  </dl>
                ) : (
                  <p className="text-sm text-text-muted">Sem pagamento registrado.</p>
                )}
              </Card>

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
                <Button
                  variant="outline"
                  loading={busy}
                  disabled={!note.trim()}
                  onClick={() => void addNote()}
                >
                  Adicionar nota
                </Button>
              </Card>
            </div>
          </div>
        )}
      </AsyncBoundary>

      <ConfirmDialog
        open={confirmDel}
        title="Excluir pedido"
        description="Isto apaga o pedido do banco permanentemente (o cliente é mantido). Não dá para desfazer."
        confirmLabel="Excluir"
        tone="danger"
        loading={busy}
        onConfirm={() => void doDelete()}
        onCancel={() => setConfirmDel(false)}
      />
    </div>
  );
}
