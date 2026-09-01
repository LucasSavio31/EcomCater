'use client';

import { useCallback, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Badge, Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { DataTable, type Column } from '@/components/data-table';
import { Select } from '@/components/form-controls';
import { StatusBadge } from '@/components/status-badge';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { useResource } from '@/lib/use-resource';
import { useToast } from '@/components/toast';
import { formatBRL } from '@/lib/format';
import { productsApi } from '@/modules/catalog/api';
import type { ProductListItem, ProductStatus } from '@/modules/catalog/types';

const PAGE_SIZE = 20;

export default function ProdutosPage() {
  const router = useRouter();
  const toast = useToast();
  const [qInput, setQInput] = useState('');
  const [q, setQ] = useState('');
  const [status, setStatus] = useState<ProductStatus | ''>('');
  const [page, setPage] = useState(1);
  const [dupId, setDupId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmBulk, setConfirmBulk] = useState(false);
  const [bulkBusy, setBulkBusy] = useState(false);

  const fetcher = useCallback(
    () => productsApi.list({ q, status, page, page_size: PAGE_SIZE }),
    [q, status, page],
  );
  const { data, loading, error, reload } = useResource(fetcher, [q, status, page]);

  const rows = useMemo(() => data?.items ?? [], [data]);
  const allChecked = rows.length > 0 && rows.every((p) => selected.has(p.id));
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
      if (allChecked) rows.forEach((p) => n.delete(p.id));
      else rows.forEach((p) => n.add(p.id));
      return n;
    });

  const bulkDelete = useCallback(async () => {
    setBulkBusy(true);
    const ids = [...selected];
    const results = await Promise.all(ids.map((id) => productsApi.remove(id)));
    setBulkBusy(false);
    setConfirmBulk(false);
    const failed = results.filter((r) => !r.ok).length;
    setSelected(new Set());
    if (failed) toast.error(`${failed} produto(s) não puderam ser excluídos.`);
    else toast.success('Produto(s) excluído(s).');
    reload();
  }, [selected, reload, toast]);

  const duplicate = useCallback(
    async (id: string) => {
      setDupId(id);
      const res = await productsApi.duplicate(id);
      setDupId(null);
      if (!res.ok) {
        toast.error(res.error.message);
        return;
      }
      toast.success('Produto duplicado.');
      router.push(`/produtos/${res.data.id}`);
    },
    [router, toast],
  );

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  const columns: Array<Column<ProductListItem>> = useMemo(
    () => [
      {
        key: 'select',
        className: 'w-10',
        header: (
          <input
            type="checkbox"
            checked={allChecked}
            onChange={toggleAll}
            aria-label="Selecionar todos"
          />
        ),
        cell: (p) => (
          <span onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              checked={selected.has(p.id)}
              onChange={() => toggle(p.id)}
              aria-label={`Selecionar ${p.name}`}
            />
          </span>
        ),
        mobileLabel: '',
      },
      {
        key: 'name',
        header: 'Produto',
        primary: true,
        cell: (p) => (
          <div className="flex items-center gap-3">
            <span className="h-10 w-10 shrink-0 overflow-hidden rounded-card bg-bg-subtle">
              {p.primary_image_url && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={p.primary_image_url} alt="" className="h-full w-full object-cover" />
              )}
            </span>
            <Link href={`/produtos/${p.id}`} className="font-medium text-accent hover:underline">
              {p.name}
            </Link>
          </div>
        ),
      },
      { key: 'status', header: 'Status', cell: (p) => <StatusBadge kind="product" value={p.status} /> },
      { key: 'price', header: 'Preço', cell: (p) => formatBRL(p.price_cents) },
      {
        key: 'stock',
        header: 'Estoque',
        cell: (p) =>
          p.in_stock ? (
            <Badge tone="success">Em estoque</Badge>
          ) : (
            <Badge tone="danger">Esgotado</Badge>
          ),
      },
      {
        key: 'featured',
        header: 'Destaque',
        cell: (p) => (p.is_featured ? <Badge tone="accent">Sim</Badge> : <span className="text-text-muted">—</span>),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [allChecked, selected],
  );

  const changeStatus = useCallback(
    async (id: string, value: ProductStatus) => {
      const res = await productsApi.setStatus(id, value);
      if (!res.ok) {
        toast.error(res.error.message);
        return;
      }
      toast.success(value === 'archived' ? 'Produto arquivado.' : 'Produto reativado.');
      reload();
    },
    [reload, toast],
  );

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Produtos"
        description="Catálogo completo da loja."
        actions={
          <Button onClick={() => router.push('/produtos/novo')}>Novo produto</Button>
        }
      />

      <Card variant="outline" className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <form
          className="flex flex-1 flex-col gap-3 sm:flex-row sm:items-end"
          onSubmit={(e) => {
            e.preventDefault();
            setPage(1);
            setQ(qInput.trim());
          }}
        >
          <Input
            label="Buscar"
            placeholder="Nome do produto"
            value={qInput}
            onChange={(e) => setQInput(e.target.value)}
            className="flex-1"
          />
          <Select
            label="Status"
            value={status}
            onChange={(e) => {
              setPage(1);
              setStatus(e.target.value as ProductStatus | '');
            }}
            placeholder="Todos"
            options={[
              { value: 'draft', label: 'Rascunho' },
              { value: 'active', label: 'Ativo' },
              { value: 'archived', label: 'Arquivado' },
            ]}
          />
          <Button type="submit" variant="outline">
            Filtrar
          </Button>
        </form>
      </Card>

      {selected.size > 0 && (
        <div className="flex flex-wrap items-center gap-3 rounded-card border border-surface-border bg-surface p-3">
          <span className="text-sm font-medium">{selected.size} selecionado(s)</span>
          <Button
            size="sm"
            variant="ghost"
            className="text-danger"
            onClick={() => setConfirmBulk(true)}
          >
            Excluir selecionados
          </Button>
          <button
            type="button"
            onClick={() => setSelected(new Set())}
            className="text-sm text-text-muted underline"
          >
            Limpar seleção
          </button>
        </div>
      )}

      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(p) => p.id}
        loading={loading}
        error={error}
        emptyMessage="Nenhum produto encontrado."
        onRowClick={(p) => router.push(`/produtos/${p.id}`)}
        rowActions={(p) => (
          <>
            <Button size="sm" variant="outline" onClick={() => router.push(`/produtos/${p.id}`)}>
              Editar
            </Button>
            <Button
              size="sm"
              variant="ghost"
              loading={dupId === p.id}
              onClick={() => void duplicate(p.id)}
            >
              Duplicar
            </Button>
            {p.status === 'archived' ? (
              <Button size="sm" variant="ghost" onClick={() => void changeStatus(p.id, 'active')}>
                Reativar
              </Button>
            ) : (
              <Button
                size="sm"
                variant="ghost"
                className="text-danger"
                onClick={() => void changeStatus(p.id, 'archived')}
              >
                Arquivar
              </Button>
            )}
          </>
        )}
      />

      {data && data.total > 0 && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-text-muted">
            {data.total} {data.total === 1 ? 'produto' : 'produtos'}
          </span>
          {totalPages > 1 && (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
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
        open={confirmBulk}
        title="Excluir produtos"
        description={`Excluir ${selected.size} produto(s) selecionado(s)? Esta ação não pode ser desfeita.`}
        confirmLabel="Excluir"
        tone="danger"
        loading={bulkBusy}
        onConfirm={() => void bulkDelete()}
        onCancel={() => setConfirmBulk(false)}
      />
    </div>
  );
}
