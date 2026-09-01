'use client';

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { Select } from '@/components/form-controls';
import { StatusBadge } from '@/components/status-badge';
import { DataTable, type Column } from '@/components/data-table';
import {
  DateRangeFilter,
  PageSizeSelect,
  DEFAULT_PAGE_SIZE,
} from '@/components/date-range-filter';
import { IconPrinter, IconTag } from '@/components/nav-icons';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { formatBRL, formatDateTime } from '@/lib/format';
import { ADMIN_API_BASE_URL } from '@/lib/admin-api-client';
import { getSession } from '@/lib/auth-storage';
import { ordersApi } from '@/modules/orders/api';
import type { OrderListItem, OrderStatus } from '@/modules/orders/types';

const STATUS_OPTIONS: Array<{ value: OrderStatus; label: string }> = [
  { value: 'pending_payment', label: 'Aguardando pagamento' },
  { value: 'paid', label: 'Gerar Envio' },
  { value: 'processing', label: 'Em separação' },
  { value: 'tracking_available', label: 'Rastreio disponível' },
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
  return (
    <Suspense fallback={null}>
      <PedidosPageInner />
    </Suspense>
  );
}

function PedidosPageInner() {
  const router = useRouter();
  const toast = useToast();
  const sp = useSearchParams();
  const [qInput, setQInput] = useState('');
  const [q, setQ] = useState('');
  const [status, setStatus] = useState<OrderStatus | ''>((sp.get('status') as OrderStatus) || '');
  const [paymentStatus, setPaymentStatus] = useState(sp.get('payment_status') || '');
  const [dateFrom, setDateFrom] = useState(sp.get('from') || '');
  const [dateTo, setDateTo] = useState(sp.get('to') || '');
  const [bucket, setBucket] = useState(sp.get('bucket') || '');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(Number(sp.get('page_size')) || DEFAULT_PAGE_SIZE);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState<string[] | null>(null);
  const [bulkStatusTo, setBulkStatusTo] = useState<OrderStatus | null>(null);
  const [busy, setBusy] = useState(false);

  const fetcher = useCallback(
    () =>
      ordersApi.list({
        q,
        status,
        payment_status: paymentStatus as never,
        date_from: dateFrom,
        date_to: dateTo,
        bucket,
        page,
        page_size: pageSize,
      }),
    [q, status, paymentStatus, dateFrom, dateTo, bucket, page, pageSize],
  );
  const { data, loading, error, reload, setData } = useResource(fetcher, [
    q,
    status,
    paymentStatus,
    dateFrom,
    dateTo,
    bucket,
    page,
    pageSize,
  ]);
  const rows = data?.items ?? [];

  // Atualização em tempo real: revalida a lista a cada 8s sem piscar a tela
  // (só troca os dados quando algo muda). Pausa fora de foco / durante ações.
  const lastSig = useRef('');
  useEffect(() => {
    const tick = async (): Promise<void> => {
      if (busy || deleting || bulkStatusTo || document.visibilityState !== 'visible') return;
      const res = await ordersApi.list({
        q,
        status,
        payment_status: paymentStatus as never,
        date_from: dateFrom,
        date_to: dateTo,
        bucket,
        page,
        page_size: pageSize,
      });
      if (!res.ok) return;
      const sig = JSON.stringify([
        res.data.total,
        res.data.items.map((o) => [
          o.number,
          o.status,
          o.payment_status,
          o.fulfillment_status,
          o.me_label,
        ]),
      ]);
      if (lastSig.current && lastSig.current !== sig) setData(res.data);
      lastSig.current = sig;
    };
    void tick();
    const id = window.setInterval(() => void tick(), 8_000);
    const onFocus = (): void => void tick();
    window.addEventListener('focus', onFocus);
    return () => {
      window.clearInterval(id);
      window.removeEventListener('focus', onFocus);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, status, paymentStatus, dateFrom, dateTo, bucket, page, pageSize, busy, deleting, bulkStatusTo]);
  const totalPages = data ? Math.max(1, Math.ceil(data.total / pageSize)) : 1;

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

  const columns: Array<Column<OrderListItem>> = [
    {
      key: 'sel',
      header: (
        <input type="checkbox" checked={allChecked} onChange={toggleAll} aria-label="Selecionar todos" />
      ),
      className: 'w-10',
      mobileLabel: '',
      stopRowClick: true,
      cell: (o) => (
        <input
          type="checkbox"
          checked={selected.has(o.number)}
          onChange={() => toggle(o.number)}
          aria-label={`Selecionar ${o.number}`}
          onClick={(e) => e.stopPropagation()}
        />
      ),
    },
    {
      key: 'number',
      header: 'Pedido',
      primary: true,
      cell: (o) => <span className="font-medium text-accent">{o.number}</span>,
    },
    {
      key: 'customer',
      header: 'Cliente',
      cell: (o) => (
        <span className="flex flex-col">
          <span className="font-medium text-text">{o.customer_name}</span>
          <span className="text-xs text-text-muted">{o.email}</span>
        </span>
      ),
    },
    {
      key: 'items',
      header: 'Itens',
      cell: (o) => (
        <span>
          {o.items_summary}
          {o.items_count > 1 && <span className="text-text-muted"> · {o.items_count} un.</span>}
          {o.suppliers.length > 0 && (
            <span className="block text-xs text-text-muted">Forn.: {o.suppliers.join(', ')}</span>
          )}
        </span>
      ),
    },
    { key: 'status', header: 'Status', cell: (o) => <StatusBadge kind="order" value={o.status} /> },
    {
      key: 'payment',
      header: 'Pagamento',
      cell: (o) => <StatusBadge kind="payment" value={o.payment_status} />,
    },
    { key: 'total', header: 'Total', cell: (o) => formatBRL(o.grand_total_cents) },
    {
      key: 'me_label',
      header: 'Etiqueta',
      cell: (o) =>
        o.me_label === 'ready' ? (
          <span className="rounded-full bg-success/10 px-2 py-0.5 text-xs font-medium text-success">
            ● liberada
          </span>
        ) : o.me_label === 'waiting' ? (
          <span className="rounded-full bg-warning/10 px-2 py-0.5 text-xs font-medium text-warning">
            aguardando
          </span>
        ) : o.me_label === 'purchased' ? (
          <span className="rounded-full bg-warning/10 px-2 py-0.5 text-xs font-medium text-warning">
            gerando…
          </span>
        ) : (
          <span className="text-xs text-text-muted">—</span>
        ),
    },
    {
      key: 'date',
      header: 'Data',
      cell: (o) => (
        <span className="text-text-muted">{formatDateTime(o.placed_at ?? o.created_at)}</span>
      ),
    },
  ];

  async function confirmDelete() {
    if (!deleting) return;
    setBusy(true);
    const results = await Promise.all(deleting.map((n) => ordersApi.remove(n)));
    setBusy(false);
    const failMsgs = results
      .filter((r): r is Extract<typeof r, { ok: false }> => !r.ok)
      .map((r) => r.error.message);
    setDeleting(null);
    setSelected(new Set());
    if (failMsgs.length) {
      toast.error(
        `${failMsgs.length} pedido(s) não excluído(s).${failMsgs[0] ? ` ${failMsgs[0]}` : ''}`,
      );
    }
    if (failMsgs.length < results.length) toast.success('Pedido(s) excluído(s).');
    reload();
  }

  async function applyBulkStatus() {
    if (!bulkStatusTo) return;
    setBusy(true);
    const res = await ordersApi.bulkStatus(selectedList, bulkStatusTo);
    setBusy(false);
    setBulkStatusTo(null);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    const fail = res.data.results.filter((r) => !r.ok);
    const ok = res.data.results.length - fail.length;
    if (ok) toast.success(`${ok} pedido(s) atualizado(s).`);
    if (fail.length) {
      toast.error(
        `${fail.length} não atualizado(s).${fail[0]?.message ? ` ${fail[0].message}` : ''}`,
      );
    }
    setSelected(new Set());
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
    if (ok) toast.success(`${ok} etiqueta(s) gerada(s) no Melhor Envio.`);
    if (fail.length) toast.error(fail[0]?.message ?? 'Alguns pedidos falharam.');
    setSelected(new Set());
    reload();
  }

  const [labelBusy, setLabelBusy] = useState(false);
  async function downloadLabels(numbers: string[]) {
    if (!numbers.length) return;
    setLabelBusy(true);
    const t = getSession()?.accessToken ?? '';
    try {
      const r = await fetch(
        `${ADMIN_API_BASE_URL}/api/admin/orders/melhor-envio/labels?numbers=${encodeURIComponent(
          numbers.join(','),
        )}`,
        { headers: { Authorization: `Bearer ${t}` } },
      );
      if (!r.ok) {
        let msg = 'Não foi possível gerar o PDF das etiquetas.';
        try {
          const j = await r.json();
          msg = j?.error?.message ?? j?.detail ?? msg;
        } catch {
          /* corpo não-JSON */
        }
        toast.error(typeof msg === 'string' ? msg : 'Falha ao gerar etiquetas.');
        return;
      }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
      setSelected(new Set());
    } catch {
      toast.error('Falha de rede ao baixar as etiquetas.');
    } finally {
      setLabelBusy(false);
    }
  }

  type SyncInfo = Extract<
    Awaited<ReturnType<typeof ordersApi.melhorEnvioSyncStatus>>,
    { ok: true }
  >['data'];
  const [syncBusy, setSyncBusy] = useState(false);
  const [syncInfo, setSyncInfo] = useState<SyncInfo | null>(null);
  const loadSyncStatus = useCallback(async () => {
    const r = await ordersApi.melhorEnvioSyncStatus();
    if (r.ok) setSyncInfo(r.data);
  }, []);
  useEffect(() => {
    void loadSyncStatus();
    const id = window.setInterval(() => void loadSyncStatus(), 20_000);
    return () => window.clearInterval(id);
  }, [loadSyncStatus]);

  async function syncTracking() {
    setSyncBusy(true);
    const res = await ordersApi.syncMelhorEnvioTracking();
    setSyncBusy(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    if (res.data.reason) toast.push(res.data.reason);
    else toast.success(`Rastreio sincronizado: ${res.data.updated ?? 0} pedido(s) atualizado(s).`);
    void loadSyncStatus();
    reload();
  }

  const fmtMin = (secs: number | null | undefined): string => {
    if (secs == null) return '—';
    if (secs < 60) return `${secs}s`;
    const m = Math.round(secs / 60);
    return `${m} min`;
  };
  const syncStatusText = (() => {
    const s = syncInfo;
    if (!s) return null;
    if (!s.enabled) return 'Sincronização automática desativada.';
    const parts = [`Sincronização automática a cada ${fmtMin(s.interval_seconds)}`];
    if (s.seconds_until_next_run != null) parts.push(`próxima em ${fmtMin(s.seconds_until_next_run)}`);
    if (s.seconds_since_last_run != null) parts.push(`última há ${fmtMin(s.seconds_since_last_run)}`);
    return parts.join(' · ');
  })();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Pedidos"
        description="Todos os pedidos da loja."
        actions={
          <div className="flex flex-col items-end gap-1">
            <Button size="sm" variant="outline" loading={syncBusy} onClick={() => void syncTracking()}>
              Sincronizar rastreio (ME)
            </Button>
            {syncStatusText && (
              <span className="text-right text-xs text-text-muted">{syncStatusText}</span>
            )}
          </div>
        }
      />

      <Card variant="outline" className="flex flex-col gap-4">
        <form
          className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"
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
              setBucket('');
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
              setBucket('');
              setPaymentStatus(e.target.value);
            }}
          />
        </form>
        <DateRangeFilter
          from={dateFrom}
          to={dateTo}
          onApply={(f, t) => {
            setPage(1);
            setBucket('');
            setDateFrom(f);
            setDateTo(t);
          }}
          onClear={() => {
            setPage(1);
            setDateFrom('');
            setDateTo('');
          }}
        />
      </Card>

      {/* Barra de ações em massa */}
      {someChecked && (
        <div className="sticky top-2 z-10 flex flex-wrap items-center gap-2 rounded-card border border-surface-border bg-surface p-3 shadow-sm">
          <span className="text-sm font-medium">{selected.size} selecionado(s)</span>
          <select
            aria-label="Mudar status dos selecionados"
            value=""
            onChange={(e) => {
              const v = e.target.value as OrderStatus;
              if (v) setBulkStatusTo(v);
              e.currentTarget.value = '';
            }}
            className="min-h-touch rounded-card border border-surface-border bg-surface px-3 text-sm"
          >
            <option value="">Mudar status para…</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
          <Link
            href={printHref('imprimir', selectedList.join(','))}
            target="_blank"
            className="inline-flex items-center gap-1.5 rounded-card border border-surface-border px-3 py-1.5 text-sm text-text hover:border-primary"
          >
            <IconPrinter width={16} height={16} /> PDF resumo (por fornecedor)
          </Link>
          <Button size="sm" variant="outline" loading={busy} onClick={() => void sendToME()}>
            Gerar etiquetas (ME)
          </Button>
          <Button
            size="sm"
            variant="outline"
            loading={labelBusy}
            onClick={() => void downloadLabels(selectedList)}
          >
            <IconTag width={16} height={16} /> Baixar etiquetas (PDF)
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

      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(o) => o.number}
        loading={loading}
        error={error}
        emptyMessage="Nenhum pedido encontrado."
        onRowClick={(o) => router.push(`/pedidos/${o.number}`)}
        rowActions={(o) => (
          <>
            <Link
              href={`/pedidos/fatura?id=${o.number}`}
              target="_blank"
              onClick={(e) => e.stopPropagation()}
              className="inline-flex items-center gap-1.5 rounded-card border border-surface-border px-2.5 py-1.5 text-xs hover:border-primary"
            >
              <IconPrinter width={14} height={14} /> Fatura
            </Link>
            <Button size="sm" variant="outline" onClick={() => router.push(`/pedidos/${o.number}`)}>
              Abrir
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="text-danger"
              onClick={() => setDeleting([o.number])}
            >
              Excluir
            </Button>
          </>
        )}
      />

      {data && data.total > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
          <div className="flex items-center gap-4">
            <span className="text-text-muted">
              {data.total} {data.total === 1 ? 'pedido' : 'pedidos'}
            </span>
            <PageSizeSelect
              value={pageSize}
              onChange={(n) => {
                setPage(1);
                setPageSize(n);
              }}
            />
          </div>
          {totalPages > 1 && (
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
          )}
        </div>
      )}

      {error && (
        <button type="button" onClick={reload} className="self-start text-sm text-accent hover:underline">
          Recarregar
        </button>
      )}

      <ConfirmDialog
        open={bulkStatusTo !== null}
        title="Mudar status em massa"
        description={
          bulkStatusTo
            ? `Mudar ${selected.size} pedido(s) para "${
                STATUS_OPTIONS.find((s) => s.value === bulkStatusTo)?.label ?? bulkStatusTo
              }"?${
                bulkStatusTo === 'canceled' || bulkStatusTo === 'refunded'
                  ? ' O estoque dos itens é devolvido.'
                  : ''
              }`
            : ''
        }
        confirmLabel="Aplicar"
        loading={busy}
        onCancel={() => setBulkStatusTo(null)}
        onConfirm={() => void applyBulkStatus()}
      />

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
