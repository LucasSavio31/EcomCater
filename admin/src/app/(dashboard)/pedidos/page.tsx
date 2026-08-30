'use client';

import { useCallback, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { Select } from '@/components/form-controls';
import { StatusBadge } from '@/components/status-badge';
import { IconEdit, IconPrinter, IconTag, IconTrash } from '@/components/nav-icons';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { formatBRL, formatDateTime } from '@/lib/format';
import { ordersApi } from '@/modules/orders/api';
import type { OrderListItem, OrderStatus } from '@/modules/orders/types';

const PAGE_SIZE = 50;

const STATUS_OPTIONS: Array<{ value: OrderStatus; label: string }> = [
  { value: 'pending_payment', label: 'Aguardando pagamento' },
  { value: 'paid', label: 'Pago' },
  { value: 'processing', label: 'Em separação' },
  { value: 'shipped', label: 'Enviado' },
  { value: 'delivered', label: 'Entregue' },
  { value: 'canceled', label: 'Cancelado' },
  { value: 'refunded', label: 'Reembolsado' },
];
const PAYMENT_OPTIONS = [
  { value: 'pending', label: 'Pendente' },
  { value: 'paid', label: 'Pago' },
  { value: 'canceled', label: 'Cancelado' },
  { value: 'refunded', label: 'Reembolsado' },
];

export default function PedidosPage() {
  const router = useRouter();
  const toast = useToast();
  const [qInput, setQInput] = useState('');
  const [q, setQ] = useState('');
  const [status, setStatus] = useState<OrderStatus | ''>('');
  const [paymentStatus, setPaymentStatus] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);

  const fetcher = useCallback(
    () =>
      ordersApi.list({
        q,
        status,
        payment_status: paymentStatus as never,
        date_from: dateFrom,
        date_to: dateTo,
        page,
        page_size: PAGE_SIZE,
      }),
    [q, status, paymentStatus, dateFrom, dateTo, page],
  );
  const { data, loading, error, reload } = useResource(fetcher, [
    q,
    status,
    paymentStatus,
    dateFrom,
    dateTo,
    page,
  ]);
  const rows = data?.items ?? [];
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  const allChecked = rows.length > 0 && rows.every((o) => selected.has(o.number));
  const someChecked = selected.size > 0;
  const selectedList = useMemo(() => [...selected], [selected]);

  function toggle(number: string) {
    setSelected((s) => {
      const n = new Set(s);
      n.has(number) ? n.delete(number) : n.add(number);
      return n;
    });
  }
  function toggleAll() {
    setSelected((s) => {
      const n = new Set(s);
      if (allChecked) rows.forEach((o) => n.delete(o.number));
      else rows.forEach((o) => n.add(o.number));
      return n;
    });
  }

  const printHref = (kind: 'imprimir' | 'etiquetas', ids: string) =>
    `/pedidos/${kind}?ids=${encodeURIComponent(ids)}`;

  async function confirmDelete() {
    if (!deleting) return;
    setBusy(true);
    const results = await Promise.all(deleting.map((n) => ordersApi.remove(n)));
    setBusy(false);
    const failed = results.filter((r) => !r.ok).length;
    setDeleting(null);
    setSelected(new Set());
    if (failed) toast.error(`${failed} pedido(s) não puderam ser excluídos.`);
    else toast.success('Pedido(s) excluído(s).');
    reload();
  }

  async function sendToME() {
    setBusy(true);
    const res = await ordersApi.sendToMelhorEnvio(selectedList);
    setBusy(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    const ok = res.data.results.filter((r) => r.ok).length;
    const fail = res.data.results.filter((r) => !r.ok);
    if (ok) toast.success(`${ok} pedido(s) enviado(s) ao Melhor Envio.`);
    if (fail.length) toast.error(fail[0]?.message ?? 'Alguns pedidos falharam.');
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Pedidos" description="Todos os pedidos da loja." />

      <Card variant="outline">
        <form
          className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5"
          onSubmit={(e) => {
            e.preventDefault();
            setPage(1);
            setQ(qInput.trim());
          }}
        >
          <Input
            label="Buscar"
            placeholder="Número ou e-mail"
            value={qInput}
            onChange={(e) => setQInput(e.target.value)}
          />
          <Select
            label="Status"
            value={status}
            placeholder="Todos"
            options={STATUS_OPTIONS}
            onChange={(e) => {
              setPage(1);
              setStatus(e.target.value as OrderStatus | '');
            }}
          />
          <Select
            label="Pagamento"
            value={paymentStatus}
            placeholder="Todos"
            options={PAYMENT_OPTIONS}
            onChange={(e) => {
              setPage(1);
              setPaymentStatus(e.target.value);
            }}
          />
          <label className="flex flex-col gap-1 text-sm font-medium text-text">
            De
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => {
                setPage(1);
                setDateFrom(e.target.value);
              }}
              className="min-h-touch rounded-card border border-surface-border bg-surface px-3 text-sm"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium text-text">
            Até
            <input
              type="date"
              value={dateTo}
              onChange={(e) => {
                setPage(1);
                setDateTo(e.target.value);
              }}
              className="min-h-touch rounded-card border border-surface-border bg-surface px-3 text-sm"
            />
          </label>
        </form>
      </Card>

      {/* Barra de ações em massa */}
      {someChecked && (
        <div className="sticky top-2 z-10 flex flex-wrap items-center gap-2 rounded-card border border-surface-border bg-surface p-3 shadow-sm">
          <span className="text-sm font-medium">{selected.size} selecionado(s)</span>
          <Link
            href={printHref('imprimir', selectedList.join(','))}
            target="_blank"
            className="inline-flex items-center gap-1.5 rounded-card border border-surface-border px-3 py-1.5 text-sm text-text hover:border-primary"
          >
            <IconPrinter width={16} height={16} /> PDF resumo (por fornecedor)
          </Link>
          <Link
            href={printHref('etiquetas', selectedList.join(','))}
            target="_blank"
            className="inline-flex items-center gap-1.5 rounded-card border border-surface-border px-3 py-1.5 text-sm text-text hover:border-primary"
          >
            <IconTag width={16} height={16} /> Etiquetas (A4, 4/página)
          </Link>
          <Button size="sm" variant="outline" loading={busy} onClick={() => void sendToME()}>
            Enviar ao Melhor Envio
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="text-danger"
            onClick={() => setDeleting(selectedList)}
          >
            Excluir selecionados
          </Button>
        </div>
      )}

      {/* Tabela */}
      <div className="overflow-x-auto rounded-card border border-surface-border">
        <table className="w-full min-w-[860px] text-sm">
          <thead className="bg-bg-subtle text-left text-xs uppercase tracking-wide text-text-muted">
            <tr>
              <th className="w-10 px-3 py-2">
                <input type="checkbox" checked={allChecked} onChange={toggleAll} aria-label="Selecionar todos" />
              </th>
              <th className="px-3 py-2">Pedido</th>
              <th className="px-3 py-2">Cliente</th>
              <th className="px-3 py-2">Itens</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Pagamento</th>
              <th className="px-3 py-2">Total</th>
              <th className="px-3 py-2">Data</th>
              <th className="px-3 py-2 text-right">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border">
            {loading && (
              <tr>
                <td colSpan={9} className="px-3 py-8 text-center text-text-muted">
                  Carregando…
                </td>
              </tr>
            )}
            {!loading && rows.length === 0 && (
              <tr>
                <td colSpan={9} className="px-3 py-8 text-center text-text-muted">
                  Nenhum pedido encontrado.
                </td>
              </tr>
            )}
            {rows.map((o: OrderListItem) => (
              <tr key={o.number} className="hover:bg-bg-subtle">
                <td className="px-3 py-2">
                  <input
                    type="checkbox"
                    checked={selected.has(o.number)}
                    onChange={() => toggle(o.number)}
                    aria-label={`Selecionar ${o.number}`}
                  />
                </td>
                <td className="px-3 py-2">
                  <Link href={`/pedidos/${o.number}`} className="font-medium text-accent hover:underline">
                    {o.number}
                  </Link>
                </td>
                <td className="px-3 py-2">
                  <span className="block font-medium text-text">{o.customer_name}</span>
                  <span className="block text-xs text-text-muted">{o.email}</span>
                </td>
                <td className="px-3 py-2">
                  {o.items_summary}
                  {o.items_count > 1 && (
                    <span className="text-text-muted"> · {o.items_count} un.</span>
                  )}
                  {o.suppliers.length > 0 && (
                    <span className="block text-xs text-text-muted">
                      Forn.: {o.suppliers.join(', ')}
                    </span>
                  )}
                </td>
                <td className="px-3 py-2">
                  <StatusBadge kind="order" value={o.status} />
                </td>
                <td className="px-3 py-2">
                  <StatusBadge kind="payment" value={o.payment_status} />
                </td>
                <td className="px-3 py-2">{formatBRL(o.grand_total_cents)}</td>
                <td className="px-3 py-2 text-text-muted">
                  {formatDateTime(o.placed_at ?? o.created_at)}
                </td>
                <td className="px-3 py-2">
                  <div className="flex items-center justify-end gap-1 text-text">
                    <Link
                      href={printHref('imprimir', o.number)}
                      target="_blank"
                      title="Gerar PDF do pedido"
                      className="rounded p-1.5 hover:bg-bg-subtle"
                    >
                      <IconPrinter width={16} height={16} />
                    </Link>
                    <button
                      type="button"
                      title="Editar"
                      onClick={() => router.push(`/pedidos/${o.number}`)}
                      className="rounded p-1.5 hover:bg-bg-subtle"
                    >
                      <IconEdit width={16} height={16} />
                    </button>
                    <button
                      type="button"
                      title="Excluir pedido"
                      onClick={() => setDeleting([o.number])}
                      className="rounded p-1.5 hover:bg-bg-subtle"
                    >
                      <IconTrash width={16} height={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data && data.total > 0 && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-text-muted">
            {data.total} {data.total === 1 ? 'pedido' : 'pedidos'}
          </span>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Anterior
            </Button>
            <span>
              Página {page} de {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Próxima
            </Button>
          </div>
        </div>
      )}

      {error && (
        <button type="button" onClick={reload} className="self-start text-sm text-accent hover:underline">
          Recarregar
        </button>
      )}

      <ConfirmDialog
        open={deleting !== null}
        title="Excluir pedido(s)"
        description={
          deleting
            ? `Isto apaga ${deleting.length} pedido(s) do banco permanentemente (o cliente é mantido). Não dá para desfazer.`
            : ''
        }
        confirmLabel="Excluir"
        tone="danger"
        loading={busy}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setDeleting(null)}
      />
    </div>
  );
}
