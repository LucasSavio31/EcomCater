'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Badge, Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Select, Textarea } from '@/components/form-controls';
import { StatusBadge, orderStatusLabel } from '@/components/status-badge';
import { IconEdit, IconPrinter, IconTag } from '@/components/nav-icons';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { formatBRL, formatDateTime } from '@/lib/format';
import { lookupCep } from '@/lib/viacep';
import { ADMIN_API_BASE_URL } from '@/lib/admin-api-client';
import { getSession } from '@/lib/auth-storage';
import { ordersApi, type OrderEditPayload } from '@/modules/orders/api';
import { type OrderDetail, type OrderStatus } from '@/modules/orders/types';

const ALL_STATUSES: OrderStatus[] = [
  'pending_payment',
  'paid',
  'processing',
  'tracking_available',
  'shipped',
  'delivered',
  'canceled',
  'refunded',
];

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

function formatCpf(cpf: string | null): string {
  if (!cpf) return '—';
  const d = cpf.replace(/\D/g, '');
  if (d.length !== 11) return cpf;
  return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`;
}

/** Máscara progressiva 000.000.000-00 */
function maskCpf(v: string): string {
  const d = v.replace(/\D/g, '').slice(0, 11);
  let out = d.slice(0, 3);
  if (d.length > 3) out += `.${d.slice(3, 6)}`;
  if (d.length > 6) out += `.${d.slice(6, 9)}`;
  if (d.length > 9) out += `-${d.slice(9, 11)}`;
  return out;
}

/** Máscara progressiva 00000-000 */
function maskCep(v: string): string {
  const d = v.replace(/\D/g, '').slice(0, 8);
  return d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d;
}

/** Máscara progressiva (99) 99999-9999 — limitada a 11 dígitos */
function maskPhone(v: string): string {
  const d = v.replace(/\D/g, '').slice(0, 11);
  if (d.length === 0) return '';
  if (d.length <= 2) return `(${d}`;
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
}

const ADDR_MASK: Partial<Record<string, (v: string) => string>> = {
  zip: maskCep,
  phone: maskPhone,
};

function VarField({
  label,
  value,
  options,
  disabled,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  disabled: boolean;
  onChange: (v: string) => void;
}) {
  if (!options || options.length === 0) {
    return (
      <Input label={label} disabled={disabled} value={value} onChange={(e) => onChange(e.target.value)} />
    );
  }
  const list = value && !options.includes(value) ? [value, ...options] : options;
  return (
    <label className="flex flex-col gap-1 text-sm font-medium text-text">
      {label}
      <select
        disabled={disabled}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="min-h-touch rounded-card border border-surface-border bg-surface px-3 text-sm text-text disabled:opacity-60"
      >
        <option value="">—</option>
        {list.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}

function buildDraft(d: OrderDetail): OrderEditPayload {
  return {
    email: d.email,
    cpf: d.cpf ?? '',
    shipping_address: { ...(d.shipping_address ?? {}) },
    shipping_service: { tracking_code: d.shipping_service?.tracking_code ?? '' },
    items: d.items
      .filter((it) => it.id)
      .map((it) => ({ id: it.id as string, cor: it.cor, numero: it.numero, name: it.name })),
  };
}

/** Link de rastreamento no site dos Correios. */
function correiosTrackingUrl(code: string): string {
  return `https://rastreamento.correios.com.br/app/index.php?objeto=${encodeURIComponent(code.trim())}`;
}

const EVENT_LABEL: Record<string, string> = {
  created: 'Pedido criado',
  note: 'Nota interna',
  tracking_added: 'Rastreio adicionado',
  tracking_update: 'Atualização de rastreio',
  edited: 'Pedido editado',
  payment_confirmed: 'Pagamento confirmado',
};

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
              {ev.to_status
                ? `Status: ${orderStatusLabel(ev.to_status)}`
                : (EVENT_LABEL[ev.type] ?? ev.type)}
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
  // o dropdown sempre reflete o último status salvo do pedido
  useEffect(() => {
    if (data?.status) setNextStatus(data.status as OrderStatus);
  }, [data?.status]);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [confirmDel, setConfirmDel] = useState(false);
  const [editMode, setEditMode] = useState(false);

  // Rascunho de edição (cliente + endereço + variação dos itens)
  const [edit, setEdit] = useState<OrderEditPayload>({});
  useEffect(() => {
    if (data) setEdit(buildDraft(data));
  }, [data]);

  // Atualiza o pedido (status + linha do tempo) sozinho, sem refresh e sem
  // piscar a tela. Bate um "pulse" leve a cada 3s e só refaz o GET completo
  // quando algo muda — rápido e sem gargalo. Pausa durante edição/ação.
  const lastPulse = useRef('');
  useEffect(() => {
    const tick = async (): Promise<void> => {
      if (editMode || busy || document.visibilityState !== 'visible') return;
      const p = await ordersApi.pulse(number);
      if (!p.ok) return;
      const sig = `${p.data.status}|${p.data.payment_status}|${p.data.fulfillment_status}|${p.data.event_count}|${p.data.last_change_at}`;
      if (lastPulse.current && lastPulse.current !== sig) {
        const res = await ordersApi.get(number);
        if (res.ok) setData(res.data);
      }
      lastPulse.current = sig;
    };
    void tick();
    const id = window.setInterval(() => void tick(), 3_000);
    const onFocus = (): void => void tick();
    window.addEventListener('focus', onFocus);
    return () => {
      window.clearInterval(id);
      window.removeEventListener('focus', onFocus);
    };
  }, [number, editMode, busy, setData]);

  const transitions = ALL_STATUSES;

  async function applyStatus(): Promise<void> {
    if (!nextStatus) return;
    setBusy(true);
    const result = await ordersApi.setStatus(number, nextStatus, statusMsg.trim() || undefined);
    setBusy(false);
    if (!result.ok) return toast.error(result.error.message);
    toast.success('Status atualizado.');
    setStatusMsg('');
    setData(result.data); // o dropdown segue o novo status via efeito
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
      cpf: (edit.cpf ?? '').replace(/\D/g, '') || null,
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
    setEditMode(false);
  }

  function cancelEdit(): void {
    if (data) setEdit(buildDraft(data));
    setEditMode(false);
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

  const [labelBusy, setLabelBusy] = useState(false);
  const [printBusy, setPrintBusy] = useState(false);
  async function downloadLabel(): Promise<void> {
    setPrintBusy(true);
    const t = getSession()?.accessToken ?? '';
    try {
      const r = await fetch(
        `${ADMIN_API_BASE_URL}/api/admin/orders/${number}/melhor-envio/label`,
        { headers: { Authorization: `Bearer ${t}` } },
      );
      if (!r.ok) {
        let msg = 'Não foi possível gerar o PDF da etiqueta.';
        try {
          const j = await r.json();
          msg = j?.error?.message ?? j?.detail ?? msg;
        } catch {
          /* corpo não-JSON */
        }
        toast.error(typeof msg === 'string' ? msg : 'Falha ao gerar a etiqueta.');
        return;
      }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch {
      toast.error('Falha de rede ao baixar a etiqueta.');
    } finally {
      setPrintBusy(false);
    }
  }
  async function generateLabel(): Promise<void> {
    setLabelBusy(true);
    const res = await ordersApi.sendToMelhorEnvio([number], true);
    setLabelBusy(false);
    if (!res.ok) return toast.error(res.error.message);
    const r = res.data.results[0];
    if (r?.ok) toast.success(r.message);
    else toast.error(r?.message ?? 'Falha ao gerar a etiqueta.');
    reload();
  }

  const setAddr = (k: string, v: string) =>
    setEdit((e) => ({ ...e, shipping_address: { ...e.shipping_address, [k]: v } }));

  async function onCepBlur() {
    const zip = String(edit.shipping_address?.zip ?? '').replace(/\D/g, '');
    if (zip.length !== 8) return;
    const found = await lookupCep(zip);
    if (!found) return;
    setEdit((e) => {
      const a = { ...(e.shipping_address ?? {}) } as Record<string, unknown>;
      a.street = a.street || found.street;
      a.district = a.district || found.district;
      a.city = a.city || found.city;
      a.state = a.state || found.state;
      return { ...e, shipping_address: a };
    });
  }
  const setItemAttr = (id: string, key: 'cor' | 'numero', v: string) =>
    setEdit((e) => ({
      ...e,
      items: e.items?.map((it) => (it.id === id ? { ...it, [key]: v } : it)),
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
            href={`/pedidos/fatura?id=${number}`}
            target="_blank"
            className="inline-flex items-center gap-1.5 rounded-card border border-surface-border px-3 py-1.5 text-sm text-text hover:border-primary"
          >
            <IconPrinter width={16} height={16} /> Fatura
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
                        <span className="text-xs text-text-muted">
                          Variação: {it.variant_label || '—'}
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

              <Card variant="outline" className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">Dados de entrega e cliente</h2>
                  {!editMode && (
                    <button
                      type="button"
                      title="Editar dados"
                      aria-label="Editar dados"
                      onClick={() => setEditMode(true)}
                      className="rounded-card border border-surface-border p-2 text-text hover:border-primary"
                    >
                      <IconEdit width={16} height={16} />
                    </button>
                  )}
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <Input
                    label="E-mail do cliente"
                    disabled={!editMode}
                    value={edit.email ?? ''}
                    onChange={(e) => setEdit((s) => ({ ...s, email: e.target.value }))}
                  />
                  <Input
                    label="CPF"
                    disabled={!editMode}
                    inputMode="numeric"
                    placeholder="000.000.000-00"
                    value={maskCpf(edit.cpf ?? '')}
                    onChange={(e) => setEdit((s) => ({ ...s, cpf: maskCpf(e.target.value) }))}
                  />
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  {ADDR_FIELDS.map((f) => (
                    <Input
                      key={f.key}
                      label={f.label}
                      disabled={!editMode}
                      inputMode={f.key === 'zip' || f.key === 'phone' ? 'numeric' : undefined}
                      placeholder={
                        f.key === 'zip'
                          ? '00000-000'
                          : f.key === 'phone'
                            ? '(11) 99999-9999'
                            : undefined
                      }
                      value={
                        ADDR_MASK[f.key]
                          ? ADDR_MASK[f.key]!((edit.shipping_address?.[f.key] as string) ?? '')
                          : ((edit.shipping_address?.[f.key] as string) ?? '')
                      }
                      onChange={(e) =>
                        setAddr(
                          f.key,
                          ADDR_MASK[f.key] ? ADDR_MASK[f.key]!(e.target.value) : e.target.value,
                        )
                      }
                      onBlur={f.key === 'zip' ? () => void onCepBlur() : undefined}
                    />
                  ))}
                </div>

                <div className="flex flex-col gap-3 border-t border-surface-border pt-3">
                  <span className="text-sm font-medium text-text">Variação dos itens</span>
                  {data.items.map((it, i) =>
                    it.id ? (
                      <div key={it.id} className="flex flex-col gap-1">
                        <span className="text-xs text-text-muted">
                          {it.name} ({it.sku})
                        </span>
                        <div className="grid gap-2 sm:grid-cols-2">
                          <VarField
                            label="Cor"
                            disabled={!editMode}
                            options={it.cor_options}
                            value={edit.items?.find((x) => x.id === it.id)?.cor ?? ''}
                            onChange={(v) => setItemAttr(it.id!, 'cor', v)}
                          />
                          <VarField
                            label="Número / tamanho"
                            disabled={!editMode}
                            options={it.numero_options}
                            value={edit.items?.find((x) => x.id === it.id)?.numero ?? ''}
                            onChange={(v) => setItemAttr(it.id!, 'numero', v)}
                          />
                        </div>
                      </div>
                    ) : (
                      <p key={i} className="text-xs text-text-muted">
                        {it.name}: variação não editável
                      </p>
                    ),
                  )}
                </div>

                <Input
                  label="Código de rastreio (tracking)"
                  disabled={!editMode}
                  hint="Preenchido automaticamente quando o Melhor Envio posta a etiqueta."
                  value={edit.shipping_service?.tracking_code ?? ''}
                  onChange={(e) =>
                    setEdit((s) => ({ ...s, shipping_service: { tracking_code: e.target.value } }))
                  }
                />

                {editMode && (
                  <div className="flex gap-2">
                    <Button loading={busy} onClick={() => void saveEdit()}>
                      Salvar alterações
                    </Button>
                    <Button variant="outline" disabled={busy} onClick={cancelEdit}>
                      Cancelar
                    </Button>
                  </div>
                )}
              </Card>

              <Card variant="outline" className="flex flex-col gap-3">
                <h2 className="text-lg font-semibold">Entrega</h2>
                <p className="text-sm">
                  <span className="text-text-muted">Método: </span>
                  {data.shipping_service?.carrier || data.shipping_method || '—'}
                  {data.shipping_service?.service ? ` · ${data.shipping_service.service}` : ''}
                </p>
                {data.customer_note && (
                  <p className="rounded-card bg-bg-subtle p-2 text-sm">
                    <span className="text-text-muted">Observação do cliente: </span>
                    {data.customer_note}
                  </p>
                )}

                <div className="flex flex-col gap-2 border-t border-surface-border pt-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium">Etiqueta Melhor Envio</span>
                    {data.shipping_service?.tracking_code ? (
                      <span className="rounded-full bg-success/10 px-2 py-0.5 text-xs font-medium text-success">
                        ● liberada — pronta p/ imprimir
                      </span>
                    ) : data.shipping_service?.label_url ? (
                      <span className="rounded-full bg-warning/10 px-2 py-0.5 text-xs font-medium text-warning">
                        aguardando o rastreio do Melhor Envio
                      </span>
                    ) : data.shipping_service?.protocol ? (
                      <span className="rounded-full bg-warning/10 px-2 py-0.5 text-xs font-medium text-warning">
                        comprada (gerando…)
                      </span>
                    ) : (
                      <span className="rounded-full bg-bg-subtle px-2 py-0.5 text-xs text-text-muted">
                        não gerada
                      </span>
                    )}
                  </div>

                  {data.shipping_service?.protocol && (
                    <p className="text-xs text-text-muted">
                      Protocolo: <span className="font-mono">{data.shipping_service.protocol}</span>
                    </p>
                  )}
                  {data.shipping_service?.tracking_code && (
                    <p className="text-xs text-text-muted">
                      Rastreio:{' '}
                      <a
                        href={correiosTrackingUrl(data.shipping_service.tracking_code)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-mono text-primary underline"
                      >
                        {data.shipping_service.tracking_code}
                      </a>
                    </p>
                  )}

                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" loading={labelBusy} onClick={() => void generateLabel()}>
                      {data.shipping_service?.label_url
                        ? 'Regerar etiqueta'
                        : 'Comprar e gerar etiqueta'}
                    </Button>
                    {data.shipping_service?.label_url && (
                      <Button
                        size="sm"
                        variant="outline"
                        loading={printBusy}
                        onClick={() => void downloadLabel()}
                      >
                        <IconTag width={16} height={16} /> Baixar etiqueta (PDF)
                      </Button>
                    )}
                  </div>
                  <p className="text-xs text-text-muted">
                    Compra usa o saldo da conta Melhor Envio. O nº do pedido vai no “Lembrete do envio”.
                  </p>
                </div>
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
                ) : data.payment_status === 'paid' ? (
                  <p className="text-sm text-text-muted">
                    Marcado como <strong className="text-success">pago</strong> manualmente — sem
                    transação de gateway registrada.
                  </p>
                ) : (
                  <p className="text-sm text-text-muted">
                    Nenhum pagamento registrado ainda (PIX/boleto aguardando confirmação).
                  </p>
                )}
              </Card>

              <Card variant="outline" className="flex flex-col gap-2">
                <h2 className="text-lg font-semibold">Cliente</h2>
                <p className="text-sm font-medium">{data.customer_name}</p>
                <p className="text-sm text-text-muted">{data.email}</p>
                <p className="text-sm">
                  <span className="text-text-muted">CPF: </span>
                  {formatCpf(data.cpf)}
                </p>
                <Badge tone="neutral">
                  Envio:{' '}
                  {{ unfulfilled: 'não enviado', partial: 'envio parcial', fulfilled: 'enviado' }[
                    data.fulfillment_status
                  ] ?? data.fulfillment_status}
                </Badge>
              </Card>

              <Card variant="outline" className="flex flex-col gap-3">
                <h2 className="text-lg font-semibold">Mudar status</h2>
                <p className="text-xs text-text-muted">
                  Status atual: <b>{orderStatusLabel(data.status)}</b>. Você pode mudar para
                  qualquer status quantas vezes precisar — cada mudança fica na linha do tempo.
                </p>
                <>
                    <Select
                      label="Novo status"
                      value={nextStatus}
                      options={transitions.map((s) => {
                        // no menu de mudança, "paid" aparece como "Pago" (o selo
                        // continua "Gerar Envio"); os demais usam o rótulo do selo.
                        const base = s === 'paid' ? 'Pago (gerar envio)' : orderStatusLabel(s);
                        return { value: s, label: s === data.status ? `${base} (atual)` : base };
                      })}
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
