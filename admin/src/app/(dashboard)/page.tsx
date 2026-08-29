'use client';

import Link from 'next/link';
import { Card } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { DataTable, type Column } from '@/components/data-table';
import { StatusBadge } from '@/components/status-badge';
import { useResource } from '@/lib/use-resource';
import { formatBRL, formatDateTime, formatNumber } from '@/lib/format';
import { dashboardApi, type DashboardRecentOrder } from '@/modules/dashboard/api';

export default function DashboardPage() {
  const { data, loading, error, reload } = useResource(() => dashboardApi.get());

  const cards = data
    ? [
        { label: 'Pedidos hoje', value: formatNumber(data.orders_today) },
        { label: 'Pedidos pendentes', value: formatNumber(data.orders_pending) },
        { label: 'Faturamento do mês', value: formatBRL(data.revenue_month_cents) },
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
              <h2 className="text-lg font-semibold">Pedidos recentes</h2>
              <Link href="/pedidos" className="text-sm text-accent hover:underline">
                Ver todos
              </Link>
            </div>
            <DataTable
              columns={columns}
              rows={data.recent_orders}
              rowKey={(o) => o.number}
              emptyMessage="Nenhum pedido recente."
            />
          </section>
        </>
      )}
    </div>
  );
}
