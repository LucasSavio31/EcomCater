'use client';

import { useEffect, useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { sizeChartsApi, type SizeChart, type SizeChartInput } from '@/modules/size-charts/api';

const EMPTY: SizeChartInput = {
  name: '',
  note: '',
  columns: ['Tamanho', 'Medida (cm)'],
  rows: [
    ['P', ''],
    ['M', ''],
    ['G', ''],
  ],
};

export default function TabelasMedidasPage() {
  const toast = useToast();
  const { data, loading, error, reload } = useResource(() => sizeChartsApi.list());
  const [form, setForm] = useState<SizeChartInput>(EMPTY);
  const [editing, setEditing] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [del, setDel] = useState<string | null>(null);

  const set = <K extends keyof SizeChartInput>(k: K, v: SizeChartInput[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  function edit(c: SizeChart) {
    setEditing(c.id);
    setForm({ name: c.name, note: c.note ?? '', columns: [...c.columns], rows: c.rows.map((r) => [...r]) });
  }
  function resetForm() {
    setEditing(null);
    setForm(EMPTY);
  }

  // mantém as linhas com o mesmo nº de colunas
  useEffect(() => {
    setForm((f) => ({
      ...f,
      rows: f.rows.map((r) => {
        const next = r.slice(0, f.columns.length);
        while (next.length < f.columns.length) next.push('');
        return next;
      }),
    }));
  }, [form.columns.length]);

  const setCell = (ri: number, ci: number, v: string) =>
    setForm((f) => ({
      ...f,
      rows: f.rows.map((r, i) => (i === ri ? r.map((c, j) => (j === ci ? v : c)) : r)),
    }));
  const setColName = (ci: number, v: string) =>
    setForm((f) => ({ ...f, columns: f.columns.map((c, i) => (i === ci ? v : c)) }));

  async function save() {
    if (!form.name.trim()) return toast.error('Dê um nome à tabela.');
    setBusy(true);
    const res = editing
      ? await sizeChartsApi.update(editing, form)
      : await sizeChartsApi.create(form);
    setBusy(false);
    if (!res.ok) return toast.error(res.error.message);
    toast.success('Tabela salva.');
    resetForm();
    reload();
  }
  async function remove() {
    if (!del) return;
    setBusy(true);
    const res = await sizeChartsApi.remove(del);
    setBusy(false);
    setDel(null);
    if (!res.ok) return toast.error(res.error.message);
    toast.success('Tabela removida.');
    reload();
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Tabelas de medidas"
        description="Cadastre as tabelas de medidas. No produto, vincule uma tabela — ela aparece num popup na página do produto."
      />

      <Card variant="outline" className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold">{editing ? 'Editar tabela' : 'Nova tabela'}</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <Input label="Nome" value={form.name} onChange={(e) => set('name', e.target.value)} />
          <Input
            label="Observação (opcional)"
            value={form.note ?? ''}
            onChange={(e) => set('note', e.target.value)}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium">Colunas</span>
          <Button
            size="sm"
            variant="outline"
            onClick={() => set('columns', [...form.columns, `Coluna ${form.columns.length + 1}`])}
          >
            + coluna
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={form.columns.length <= 1}
            onClick={() => set('columns', form.columns.slice(0, -1))}
          >
            − coluna
          </Button>
        </div>

        <div className="overflow-x-auto rounded-card border border-surface-border">
          <table className="w-full min-w-[420px] text-sm">
            <thead className="bg-bg-subtle">
              <tr>
                {form.columns.map((c, ci) => (
                  <th key={ci} className="p-1">
                    <input
                      value={c}
                      onChange={(e) => setColName(ci, e.target.value)}
                      className="w-full rounded-card border border-surface-border bg-surface px-2 py-1 text-xs font-semibold"
                    />
                  </th>
                ))}
                <th className="w-8" />
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {form.rows.map((r, ri) => (
                <tr key={ri}>
                  {r.map((cell, ci) => (
                    <td key={ci} className="p-1">
                      <input
                        value={cell}
                        onChange={(e) => setCell(ri, ci, e.target.value)}
                        className="w-full rounded-card border border-surface-border bg-surface px-2 py-1"
                      />
                    </td>
                  ))}
                  <td className="p-1 text-center">
                    <button
                      type="button"
                      aria-label="Remover linha"
                      className="text-text-muted hover:text-danger"
                      onClick={() => set('rows', form.rows.filter((_, i) => i !== ri))}
                    >
                      ×
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Button
          size="sm"
          variant="outline"
          className="self-start"
          onClick={() => set('rows', [...form.rows, form.columns.map(() => '')])}
        >
          + linha
        </Button>

        <div className="flex gap-2">
          <Button loading={busy} onClick={() => void save()}>
            {editing ? 'Salvar' : 'Adicionar'}
          </Button>
          {editing && (
            <Button variant="outline" onClick={resetForm}>
              Cancelar
            </Button>
          )}
        </div>
      </Card>

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        <div className="flex flex-col gap-2">
          {(data ?? []).map((c) => (
            <Card key={c.id} variant="outline" className="flex flex-wrap items-center gap-3">
              <span className="text-sm font-medium">{c.name}</span>
              <span className="text-xs text-text-muted">
                {c.columns.length} colunas · {c.rows.length} linhas
              </span>
              <div className="ml-auto flex gap-2">
                <Button size="sm" variant="outline" onClick={() => edit(c)}>
                  Editar
                </Button>
                <Button size="sm" variant="ghost" className="text-danger" onClick={() => setDel(c.id)}>
                  Excluir
                </Button>
              </div>
            </Card>
          ))}
          {(data ?? []).length === 0 && (
            <p className="text-sm text-text-muted">Nenhuma tabela cadastrada.</p>
          )}
        </div>
      </AsyncBoundary>

      <ConfirmDialog
        open={del !== null}
        title="Excluir tabela de medidas"
        description="Produtos que usam esta tabela ficam sem tabela."
        confirmLabel="Excluir"
        tone="danger"
        loading={busy}
        onConfirm={() => void remove()}
        onCancel={() => setDel(null)}
      />
    </div>
  );
}
