'use client';

import { useCallback, useState } from 'react';
import { Button, Card } from '@ecom/ui';
import { Select } from '@/components/form-controls';
import { StatusBadge } from '@/components/status-badge';
import { AsyncBoundary } from '@/components/async-boundary';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { formatDateTime } from '@/lib/format';
import { productsApi } from '@/modules/catalog/api';

export function ReviewsTab({ productId }: { productId: string }) {
  const toast = useToast();
  const [statusFilter, setStatusFilter] = useState('');
  const fetcher = useCallback(
    () => productsApi.reviews(productId, statusFilter || undefined),
    [productId, statusFilter],
  );
  const { data, loading, error, reload } = useResource(fetcher, [productId, statusFilter]);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function moderate(id: string, status: 'approved' | 'rejected' | 'pending'): Promise<void> {
    setBusyId(id);
    const result = await productsApi.moderateReview(productId, id, status);
    setBusyId(null);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success('Avaliação atualizada.');
    reload();
  }

  return (
    <Card variant="outline" className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold">Avaliações</h3>
        <Select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          placeholder="Todas"
          options={[
            { value: 'pending', label: 'Pendentes' },
            { value: 'approved', label: 'Aprovadas' },
            { value: 'rejected', label: 'Rejeitadas' },
          ]}
        />
      </div>

      <AsyncBoundary
        loading={loading}
        error={error}
        onRetry={reload}
        empty={(data?.length ?? 0) === 0}
        emptyMessage="Nenhuma avaliação."
      >
        <ul className="flex flex-col gap-3">
          {(data ?? []).map((r) => (
            <li key={r.id} className="flex flex-col gap-2 rounded-card border border-surface-border p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium">
                  {r.author_name} · {'★'.repeat(r.rating)}
                  <span className="text-text-muted">{'★'.repeat(Math.max(0, 5 - r.rating))}</span>
                </span>
                <StatusBadge kind="review" value={r.status} />
              </div>
              {r.title && <p className="text-sm font-medium">{r.title}</p>}
              {r.body && <p className="text-sm text-text-muted">{r.body}</p>}
              <span className="text-xs text-text-muted">{formatDateTime(r.created_at)}</span>
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={busyId === r.id || r.status === 'approved'}
                  onClick={() => void moderate(r.id, 'approved')}
                >
                  Aprovar
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={busyId === r.id || r.status === 'rejected'}
                  onClick={() => void moderate(r.id, 'rejected')}
                >
                  Rejeitar
                </Button>
                {r.status !== 'pending' && (
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={busyId === r.id}
                    onClick={() => void moderate(r.id, 'pending')}
                  >
                    Voltar a pendente
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </AsyncBoundary>
    </Card>
  );
}
