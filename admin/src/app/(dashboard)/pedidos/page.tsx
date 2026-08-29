'use client';

import { useCallback, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { DataTable, type Column } from '@/components/data-table';
import { Select } from '@/components/form-controls';
import { StatusBadge } from '@/components/status-badge';
import { useResource } from '@/lib/use-resource';
import { formatBRL, formatDateTime } from '@/lib/format';
import { ordersApi } from '@/modules/orders/api';
import type { OrderListItem, OrderStatus } from '@/modules/orders/types';

const PAGE_SIZE = 20;

const STATUS_OPTIONS: Array<{ value: OrderStatus; label: string }> = [
  { value: 'pending_payment', label: 'Aguardando pagamento' },
  { value: 'paid', label: 'Pago' },
  { value: 'processing', label: 'Em separação' },
  { value: 'shipped', label: 'Enviado' },
  { value: 'delivered', label: 'Entregue' },
  { value: 'canceled', label: 'Cancelado' },
  { value: 'refunded', label: 'Reembolsado' },
];

export default function PedidosPage() {
  const router = useRouter();
  const [qInput, setQInput] = useState('');
  const [q, setQ] = useState('');
  const [status, setStatus] = useState<OrderStatus | ''>('');
  const [page, setPage] = useState(1);

  const fetcher = useCallback(
    () => ordersApi.list({ q, status, page, page_size: PAGE_SIZE }),
    [q, status, page],
  );
  const { data, loading, error, reload } = useResource(fetcher, [q, status, page]);
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  const columns: Array<Column<OrderListItem>> = [
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
    { key: 'email', header: 'Cliente', cell: (o) => o.email },
    { key: 'status', header: 'Status', cell: (o) => <StatusBadge kind="order" value={o.status} /> },
    {
      key: 'payment',
      header: 'Pagamento',
      cell: (o) => <StatusBadge kind="payment" value={o.payment_status} />,
    },
    { key: 'total', header: 'Total', cell: (o) => formatBRL(o.grand_total_cents) },
    { key: 'placed_at', header: 'Data', cell: (o) => formatDateTime(o.placed_at) },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Pedidos" description="Todos os pedidos da loja." />

      <Card variant="outline">
        <form
          className="flex flex-col gap-3 sm:flex-row sm:items-end"
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
            className="flex-1"
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
          <Button type="submit" variant="outline">
            Filtrar
          </Button>
        </form>
      </Card>

      <DataTable
        columns={columns}
        rows={data?.items ?? []}
        rowKey={(o) => o.number}
        loading={loading}
        error={error}
        emptyMessage="Nenhum pedido encontrado."
        onRowClick={(o) => router.push(`/pedidos/${o.number}`)}
      />

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
    </div>
  );
}
