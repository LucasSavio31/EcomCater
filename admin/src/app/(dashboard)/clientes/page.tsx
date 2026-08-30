'use client';

import { useCallback, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { DataTable, type Column } from '@/components/data-table';
import { AsyncBoundary } from '@/components/async-boundary';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { formatBRL, formatDateTime } from '@/lib/format';
import { maskPhone } from '@/lib/phone';
import { customersApi, type CustomerListItem } from '@/modules/customers/api';

const PAGE_SIZE = 25;

function fmtCpf(cpf: string | null): string {
  if (!cpf) return '—';
  const d = cpf.replace(/\D/g, '');
  return d.length === 11 ? `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}` : cpf;
}

export default function ClientesPage() {
  const router = useRouter();
  const toast = useToast();
  const [qInput, setQInput] = useState('');
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmDel, setConfirmDel] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const fetcher = useCallback(() => customersApi.list(q, page), [q, page]);
  const { data, loading, error, reload } = useResource(fetcher, [q, page]);
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  const rows = data?.items ?? [];
  const allChecked = rows.length > 0 && rows.every((c) => selected.has(c.id));
  const toggle = (id: string) =>
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  const toggleAll = () =>
    setSelected((s) => {
      const n = new Set(s);
      if (allChecked) rows.forEach((c) => n.delete(c.id));
      else rows.forEach((c) => n.add(c.id));
      return n;
    });

  async function deleteSelected() {
    setDeleting(true);
    const res = await customersApi.removeMany([...selected]);
    setDeleting(false);
    setConfirmDel(false);
    if (!res.ok) return toast.error(res.error.message);
    toast.success(`${res.data.deleted} cliente(s) excluído(s). Os pedidos foram preservados.`);
    setSelected(new Set());
    reload();
  }

  const columns: Array<Column<CustomerListItem>> = [
    {
      key: 'select',
      header: (
        <input
          type="checkbox"
          checked={allChecked}
          onChange={toggleAll}
          aria-label="Selecionar todos"
        />
      ),
      primary: true,
      cell: (c) => (
        <input
          type="checkbox"
          checked={selected.has(c.id)}
          onChange={() => toggle(c.id)}
          onClick={(e) => e.stopPropagation()}
          aria-label={`Selecionar ${c.full_name || c.email}`}
        />
      ),
    },
    { key: 'name', header: 'Nome', cell: (c) => c.full_name || '—' },
    { key: 'email', header: 'E-mail', cell: (c) => c.email },
    { key: 'phone', header: 'Telefone', cell: (c) => (c.phone ? maskPhone(c.phone) : '—') },
    { key: 'cpf', header: 'CPF', cell: (c) => fmtCpf(c.cpf) },
    { key: 'orders', header: 'Pedidos', cell: (c) => c.orders_count },
    { key: 'total', header: 'Total gasto', cell: (c) => formatBRL(c.total_spent_cents) },
    {
      key: 'created',
      header: 'Cadastro',
      cell: (c) => (c.created_at ? formatDateTime(c.created_at) : '—'),
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Clientes"
        description="Cadastro dos clientes da loja. Editar dados aqui atualiza também os pedidos ativos."
      />

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
            value={qInput}
            onChange={(e) => setQInput(e.target.value)}
            placeholder="Nome, e-mail ou CPF"
            className="flex-1"
          />
          <Button type="submit" variant="outline">
            Buscar
          </Button>
        </form>
      </Card>

      {selected.size > 0 && (
        <div className="flex items-center gap-3">
          <span className="text-sm text-text-muted">{selected.size} selecionado(s)</span>
          <Button size="sm" variant="ghost" className="text-danger" onClick={() => setConfirmDel(true)}>
            Excluir selecionados ({selected.size})
          </Button>
        </div>
      )}

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        <DataTable
          columns={columns}
          rows={rows}
          rowKey={(c) => c.id}
          emptyMessage="Nenhum cliente encontrado."
          onRowClick={(c) => router.push(`/clientes/${c.id}`)}
        />
      </AsyncBoundary>

      {data && data.total > PAGE_SIZE && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-text-muted">{data.total} clientes</span>
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

      <ConfirmDialog
        open={confirmDel}
        title="Excluir clientes"
        description={`Excluir ${selected.size} cliente(s)? O histórico de pedidos é mantido — os pedidos ficam sem conta vinculada.`}
        confirmLabel="Excluir"
        tone="danger"
        loading={deleting}
        onConfirm={() => void deleteSelected()}
        onCancel={() => setConfirmDel(false)}
      />
    </div>
  );
}
