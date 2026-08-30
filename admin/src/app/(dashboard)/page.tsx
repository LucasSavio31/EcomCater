'use client';

import { useCallback, useState } from 'react';
import Link from 'next/link';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { DataTable, type Column } from '@/components/data-table';
import { StatusBadge } from '@/components/status-badge';
import { useResource } from '@/lib/use-resource';
import { formatBRL, formatDateTime, formatNumber } from '@/lib/format';
import { dashboardApi, type DashboardRecentOrder } from '@/modules/dashboard/api';

function todayISO(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function monthStartISO(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`;
}
/** "2026-08-29" -> ISO no fuso local do navegador (início/fim do dia). */
function dayBoundISO(ymd: string, end: boolean): string {
  const [y, m, d] = ymd.split('-').map(Number);
  const dt = end
    ? new Date(y, m - 1, d, 23, 59, 59, 999)
    : new Date(y, m - 1, d, 0, 0, 0, 0);
  return dt.toISOString();
}

export default function DashboardPage() {
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [applied, setApplied] = useState<{ from: string; to: string }>({ from: '', to: '' });
  const ranged = applied.from !== '' || applied.to !== '';

  const fetcher = useCallback(
    () =>
      dashboardApi.get({
        from: applied.from ? dayBoundISO(applied.from, false) : undefined,
        to: applied.to ? dayBoundISO(applied.to, true) : undefined,
      }),
    [applied.from, applied.to],
  );
  const { data, loading, error, reload } = useResource(fetcher, [applied.from, applied.to]);

  function apply() {
    setApplied({ from, to });
  }
  function clear() {
    setFrom('');
    setTo('');
    setApplied({ from: '', to: '' });
  }
  function thisMonth() {
    const f = monthStartISO();
    const t = todayISO();
    setFrom(f);
    setTo(t);
    setApplied({ from: f, to: t });
  }

  const cards = data
    ? [
        {
          label: ranged ? 'Pedidos no período' : 'Pedidos hoje',
          value: formatNumber(data.orders_today),
        },
        { label: 'Pedidos pendentes', value: formatNumber(data.orders_pending) },
        {
          label: ranged ? 'Faturamento no período' : 'Faturamento do mês',
          value: formatBRL(data.revenue_month_cents),
        },
        { label: 'Estoque baixo', value: formatNumber(data.low_stock_count) },
      ]
    : [];

  const columns: Array<Column<DashboardRecentOrder>> = [
    {
      key: 'number',
      header: 'Pedido',
      primary: true,
      cell: (o) => (
        <Link href={`/pedidos/${o.number}`} className="font-medium text-accent hover:underline">
          {o.number}
        </Link>
      ),
    },
    { key: 'email', header: 'Cliente', mobileLabel: 'Cliente', cell: (o) => o.email },
    { key: 'status', header: 'Status', cell: (o) => <StatusBadge kind="order" value={o.status} /> },
    {
      key: 'payment',
      header: 'Pagamento',
      cell: (o) => <StatusBadge kind="payment" value={o.payment_status} />,
    },
    { key: 'total', header: 'Total', cell: (o) => formatBRL(o.total_cents) },
    { key: 'placed_at', header: 'Data', cell: (o) => formatDateTime(o.placed_at) },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Dashboard" description="Visão geral da loja." />

      <Card variant="outline" className="flex flex-col gap-3">
        <div className="flex flex-wrap items-end gap-3">
          <Input
            type="date"
            label="De"
            value={from}
            max={to || undefined}
            onChange={(e) => setFrom(e.target.value)}
          />
          <Input
            type="date"
            label="Até"
            value={to}
            min={from || undefined}
            onChange={(e) => setTo(e.target.value)}
          />
          <Button onClick={apply}>Aplicar</Button>
          <Button variant="outline" onClick={thisMonth}>
            Este mês
          </Button>
          {ranged && (
            <Button variant="ghost" onClick={clear}>
              Limpar
            </Button>
          )}
        </div>
        <p className="text-xs text-text-muted">
          {ranged
            ? 'Pedidos e faturamento consideram o período selecionado. “Pedidos pendentes” e “Estoque baixo” são sempre a foto atual.'
            : 'Sem filtro: “Pedidos hoje” conta o dia de hoje e “Faturamento” considera o mês atual.'}
        </p>
      </Card>

      {loading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Card key={i} variant="elevated" className="h-24 animate-pulse bg-bg-subtle" />
          ))}
        </div>
      )}

      {error && (
        <Card variant="outline" className="border-danger">
          <p className="text-sm text-danger">Falha ao carregar: {error}</p>
          <button type="button" onClick={reload} className="mt-2 text-sm text-accent hover:underline">
            Tentar de novo
          </button>
        </Card>
      )}

      {data && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {cards.map((card) => (
              <Card key={card.label} variant="elevated" className="flex flex-col gap-1">
                <span className="text-sm text-text-muted">{card.label}</span>
                <span className="text-2xl font-semibold">{card.value}</span>
              </Card>
            ))}
          </div>

          <section className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">
                {ranged ? 'Pedidos do período' : 'Pedidos recentes'}
              </h2>
              <Link href="/pedidos" className="text-sm text-accent hover:underline">
                Ver todos
              </Link>
            </div>
            <DataTable
              columns={columns}
              rows={data.recent_orders}
              rowKey={(o) => o.number}
              emptyMessage="Nenhum pedido no período."
            />
          </section>
        </>
      )}
    </div>
  );
}
