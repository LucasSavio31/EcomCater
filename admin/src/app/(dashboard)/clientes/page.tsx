'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { DataTable, type Column } from '@/components/data-table';
import { AsyncBoundary } from '@/components/async-boundary';
import { StatusBadge } from '@/components/status-badge';
import { useResource } from '@/lib/use-resource';
import { formatBRL, formatDateTime } from '@/lib/format';
import { fetchCustomers, customersApi, type CustomerSummary } from '@/modules/customers/api';

export default function ClientesPage() {
  const { data, loading, error, reload } = useResource(() => fetchCustomers());
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const list = data ?? [];
    const term = search.trim().toLowerCase();
    return term ? list.filter((c) => c.email.toLowerCase().includes(term)) : list;
  }, [data, search]);

  const columns: Array<Column<CustomerSummary>> = [
    { key: 'email', header: 'E-mail', primary: true, cell: (c) => c.email },
    { key: 'orders', header: 'Pedidos', cell: (c) => c.orders_count },
    { key: 'total', header: 'Total gasto', cell: (c) => formatBRL(c.total_spent_cents) },
    { key: 'last', header: 'Último pedido', cell: (c) => formatDateTime(c.last_order_at) },
    { key: 'status', header: 'Último status', cell: (c) => <StatusBadge kind="order" value={c.last_status} /> },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Clientes"
        description="Derivado dos pedidos (agrupado por e-mail). Um endpoint dedicado virá depois."
      />

      <Card variant="outline">
        <Input
          label="Buscar por e-mail"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="cliente@email.com"
        />
      </Card>

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        <DataTable
          columns={columns}
          rows={filtered}
          rowKey={(c) => c.email}
          emptyMessage="Nenhum cliente ainda."
          onRowClick={(c) => setSelected((prev) => (prev === c.email ? null : c.email))}
        />
      </AsyncBoundary>

      {selected && <CustomerOrders email={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function CustomerOrders({ email, onClose }: { email: string; onClose: () => void }) {
  const { data, loading, error, reload } = useResource(() => customersApi.ordersByEmail(email), [email]);

  return (
    <Card variant="elevated" className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Pedidos de {email}</h2>
        <Button variant="ghost" size="sm" onClick={onClose}>
          Fechar
        </Button>
      </div>
      <AsyncBoundary
        loading={loading}
        error={error}
        onRetry={reload}
        empty={(data?.items.length ?? 0) === 0}
        emptyMessage="Nenhum pedido."
      >
        <ul className="flex flex-col divide-y divide-surface-border">
          {(data?.items ?? []).map((o) => (
            <li key={o.number} className="flex items-center justify-between gap-3 py-2 text-sm">
              <Link href={`/pedidos/${o.number}`} className="font-medium text-accent hover:underline">
                {o.number}
              </Link>
              <StatusBadge kind="order" value={o.status} />
              <span>{formatBRL(o.grand_total_cents)}</span>
              <span className="text-text-muted">{formatDateTime(o.placed_at)}</span>
            </li>
          ))}
        </ul>
      </AsyncBoundary>
    </Card>
  );
}
