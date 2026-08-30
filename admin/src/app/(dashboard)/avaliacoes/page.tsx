'use client';

import { useCallback, useState } from 'react';
import { Badge, Button, Card } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { Select } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { formatDateTime } from '@/lib/format';
import { productsApi } from '@/modules/catalog/api';
import type { AdminReview } from '@/modules/catalog/types';

const STATUS_LABEL: Record<string, { label: string; tone: 'warning' | 'success' | 'danger' }> = {
  pending: { label: 'Pendente', tone: 'warning' },
  approved: { label: 'Aprovada', tone: 'success' },
  rejected: { label: 'Rejeitada', tone: 'danger' },
};

export default function AvaliacoesPage() {
  const toast = useToast();
  const [status, setStatus] = useState('pending');
  const [page, setPage] = useState(1);
  const [busyId, setBusyId] = useState<string | null>(null);

  const fetcher = useCallback(
    () => productsApi.allReviews(status || undefined, page),
    [status, page],
  );
  const { data, loading, error, reload } = useResource(fetcher, [status, page]);
  const rows = data?.items ?? [];
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  async function moderate(r: AdminReview, next: 'approved' | 'rejected' | 'pending') {
    setBusyId(r.id);
    const res = await productsApi.moderateAnyReview(r.id, next);
    setBusyId(null);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    toast.success('Avaliação atualizada.');
    reload();
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Avaliações"
        description="Modere as avaliações enviadas pelos clientes. Só clientes logados podem avaliar."
      />

      <Card variant="outline" className="flex flex-wrap items-end gap-3">
        <Select
          label="Status"
          value={status}
          placeholder="Todas"
          options={[
            { value: 'pending', label: 'Pendentes' },
            { value: 'approved', label: 'Aprovadas' },
            { value: 'rejected', label: 'Rejeitadas' },
          ]}
          onChange={(e) => {
            setPage(1);
            setStatus(e.target.value);
          }}
        />
      </Card>

      {loading && <p className="text-sm text-text-muted">Carregando…</p>}
      {error && (
        <button type="button" onClick={reload} className="self-start text-sm text-accent hover:underline">
          Recarregar
        </button>
      )}

      {!loading && rows.length === 0 && (
        <Card variant="outline" className="text-center text-sm text-text-muted">
          Nenhuma avaliação {status ? `${STATUS_LABEL[status]?.label.toLowerCase()}` : ''}.
        </Card>
      )}

      <div className="flex flex-col gap-3">
        {rows.map((r) => {
          const st = STATUS_LABEL[r.status];
          return (
            <Card key={r.id} variant="outline" className="flex flex-col gap-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold">{'★'.repeat(r.rating)}</span>
                  <span className="text-sm text-text-muted">{'☆'.repeat(5 - r.rating)}</span>
                  {st && <Badge tone={st.tone}>{st.label}</Badge>}
                </div>
                <span className="text-xs text-text-muted">{formatDateTime(r.created_at)}</span>
              </div>
              <p className="text-sm">
                <span className="text-text-muted">Produto: </span>
                {r.product_name}
              </p>
              <p className="text-sm">
                <span className="text-text-muted">Cliente: </span>
                {r.author_name}
              </p>
              {r.title && <p className="text-sm font-medium">{r.title}</p>}
              {r.body && <p className="text-sm text-text-muted">{r.body}</p>}
              <div className="flex flex-wrap gap-2 pt-1">
                {r.status !== 'approved' && (
                  <Button
                    size="sm"
                    loading={busyId === r.id}
                    onClick={() => void moderate(r, 'approved')}
                  >
                    Aprovar
                  </Button>
                )}
                {r.status !== 'rejected' && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-danger"
                    loading={busyId === r.id}
                    onClick={() => void moderate(r, 'rejected')}
                  >
                    Rejeitar
                  </Button>
                )}
                {r.status !== 'pending' && (
                  <Button
                    size="sm"
                    variant="ghost"
                    loading={busyId === r.id}
                    onClick={() => void moderate(r, 'pending')}
                  >
                    Voltar p/ pendente
                  </Button>
                )}
              </div>
            </Card>
          );
        })}
      </div>

      {data && data.total > data.page_size && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-text-muted">{data.total} avaliações</span>
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
    </div>
  );
}
