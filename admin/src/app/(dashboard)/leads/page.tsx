'use client';

import { useMemo, useState } from 'react';
import { Badge, Card } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { Select } from '@/components/form-controls';
import { AsyncBoundary } from '@/components/async-boundary';
import { useResource } from '@/lib/use-resource';
import { formatDateTime } from '@/lib/format';
import { leadsApi, SOURCE_LABEL } from '@/modules/leads/api';

export default function LeadsPage() {
  const { data, loading, error, reload } = useResource(() => leadsApi.list());
  const [source, setSource] = useState('');

  const rows = useMemo(() => {
    const all = data ?? [];
    return source ? all.filter((l) => l.source === source) : all;
  }, [data, source]);

  const sources = useMemo(
    () => Array.from(new Set((data ?? []).map((l) => l.source))),
    [data],
  );

  function exportCsv() {
    const head = ['nome', 'email', 'telefone', 'origem', 'cupom', 'inscrito', 'data'];
    const lines = rows.map((l) =>
      [
        l.name ?? '',
        l.email,
        l.phone ?? '',
        SOURCE_LABEL[l.source] ?? l.source,
        l.coupon_code ?? '',
        l.subscribed ? 'sim' : 'não',
        l.created_at ?? '',
      ]
        .map((v) => `"${String(v).replace(/"/g, '""')}"`)
        .join(','),
    );
    const blob = new Blob([[head.join(','), ...lines].join('\n')], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `leads-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Leads"
        description="Cadastros do popup, do formulário da home e de quem comprou. Base para campanhas de e-mail."
        actions={
          <button
            type="button"
            onClick={exportCsv}
            className="rounded-btn border border-surface-border px-3 py-1.5 text-sm hover:border-primary"
          >
            Exportar CSV
          </button>
        }
      />

      <Card variant="outline" className="flex flex-wrap items-end gap-3">
        <Select
          label="Origem"
          value={source}
          placeholder="Todas"
          options={sources.map((s) => ({ value: s, label: SOURCE_LABEL[s] ?? s }))}
          onChange={(e) => setSource(e.target.value)}
        />
        <span className="text-sm text-text-muted">{rows.length} lead(s)</span>
      </Card>

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        <div className="overflow-x-auto rounded-card border border-surface-border">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="bg-bg-subtle text-left text-xs uppercase tracking-wide text-text-muted">
              <tr>
                <th className="px-3 py-2">Nome</th>
                <th className="px-3 py-2">E-mail</th>
                <th className="px-3 py-2">Telefone</th>
                <th className="px-3 py-2">Origem</th>
                <th className="px-3 py-2">Cupom</th>
                <th className="px-3 py-2">Data</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {rows.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-8 text-center text-text-muted">
                    Nenhum lead.
                  </td>
                </tr>
              )}
              {rows.map((l) => (
                <tr key={l.id} className={l.subscribed ? '' : 'opacity-50'}>
                  <td className="px-3 py-2">{l.name ?? '—'}</td>
                  <td className="px-3 py-2">{l.email}</td>
                  <td className="px-3 py-2">{l.phone ?? '—'}</td>
                  <td className="px-3 py-2">
                    <Badge tone="neutral">{SOURCE_LABEL[l.source] ?? l.source}</Badge>
                  </td>
                  <td className="px-3 py-2">{l.coupon_code ?? '—'}</td>
                  <td className="px-3 py-2 text-text-muted">
                    {l.created_at ? formatDateTime(l.created_at) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </AsyncBoundary>
    </div>
  );
}
