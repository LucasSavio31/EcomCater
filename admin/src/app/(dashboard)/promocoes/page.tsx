'use client';

import { useState } from 'react';
import { Badge, Button, Card, Input, Modal } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { DataTable, type Column } from '@/components/data-table';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox, Select } from '@/components/form-controls';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { centsToInput, formatBRL, formatDate, inputToCents } from '@/lib/format';
import { promotionsApi, type Promotion, type PromotionInput, type PromotionType } from '@/modules/promotions/api';

interface FormState {
  code: string;
  description: string;
  type: PromotionType;
  value: string;
  min_order: string;
  max_discount: string;
  starts_at: string;
  ends_at: string;
  usage_limit: string;
  usage_limit_per_user: string;
  is_active: boolean;
}

const EMPTY: FormState = {
  code: '',
  description: '',
  type: 'percent',
  value: '',
  min_order: '',
  max_discount: '',
  starts_at: '',
  ends_at: '',
  usage_limit: '',
  usage_limit_per_user: '',
  is_active: true,
};

function toForm(p: Promotion): FormState {
  return {
    code: p.code,
    description: p.description ?? '',
    type: p.type,
    value: p.type === 'fixed' ? centsToInput(p.value) : String(p.value),
    min_order: centsToInput(p.min_order_cents),
    max_discount: centsToInput(p.max_discount_cents),
    starts_at: p.starts_at ? p.starts_at.slice(0, 10) : '',
    ends_at: p.ends_at ? p.ends_at.slice(0, 10) : '',
    usage_limit: p.usage_limit != null ? String(p.usage_limit) : '',
    usage_limit_per_user: p.usage_limit_per_user != null ? String(p.usage_limit_per_user) : '',
    is_active: p.is_active,
  };
}

function buildPayload(f: FormState): PromotionInput {
  const rawValue = f.type === 'fixed' ? inputToCents(f.value) ?? 0 : Number(f.value) || 0;
  return {
    code: f.code.trim(),
    description: f.description.trim() || null,
    type: f.type,
    value: rawValue,
    min_order_cents: inputToCents(f.min_order),
    max_discount_cents: inputToCents(f.max_discount),
    starts_at: f.starts_at ? new Date(f.starts_at).toISOString() : null,
    ends_at: f.ends_at ? new Date(f.ends_at).toISOString() : null,
    usage_limit: f.usage_limit ? Number(f.usage_limit) : null,
    usage_limit_per_user: f.usage_limit_per_user ? Number(f.usage_limit_per_user) : null,
    is_active: f.is_active,
  };
}

const TYPE_LABEL: Record<PromotionType, string> = {
  percent: 'Percentual',
  fixed: 'Valor fixo',
  free_shipping: 'Frete grátis',
};

export default function PromocoesPage() {
  const toast = useToast();
  const { data, loading, error, reload } = useResource(() => promotionsApi.list());

  const [editing, setEditing] = useState<Promotion | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Promotion | null>(null);
  const [deleting, setDeleting] = useState(false);

  const open = creating || editing !== null;
  const set = <K extends keyof FormState>(k: K, v: FormState[K]): void =>
    setForm((prev) => ({ ...prev, [k]: v }));

  function openCreate(): void {
    setForm(EMPTY);
    setEditing(null);
    setCreating(true);
  }
  function openEdit(p: Promotion): void {
    setForm(toForm(p));
    setCreating(false);
    setEditing(p);
  }
  function close(): void {
    setCreating(false);
    setEditing(null);
  }

  async function save(): Promise<void> {
    if (!form.code.trim()) {
      toast.error('Informe o código do cupom.');
      return;
    }
    setSaving(true);
    const payload = buildPayload(form);
    const result = editing
      ? await promotionsApi.update(editing.id, payload)
      : await promotionsApi.create(payload);
    setSaving(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success(editing ? 'Cupom salvo.' : 'Cupom criado.');
    close();
    reload();
  }

  async function confirmDelete(): Promise<void> {
    if (!deleteTarget) return;
    setDeleting(true);
    const result = await promotionsApi.remove(deleteTarget.id);
    setDeleting(false);
    if (!result.ok) {
      toast.error(
        result.error.status === 409
          ? 'Cupom já utilizado em pedidos — não pode ser excluído. Desative-o.'
          : result.error.message,
      );
      setDeleteTarget(null);
      return;
    }
    toast.success('Cupom excluído.');
    setDeleteTarget(null);
    reload();
  }

  const columns: Array<Column<Promotion>> = [
    {
      key: 'code',
      header: 'Código',
      primary: true,
      cell: (p) => (
        <span className="font-mono font-medium">
          {p.code} {!p.is_active && <Badge tone="neutral">inativo</Badge>}
        </span>
      ),
    },
    { key: 'type', header: 'Tipo', cell: (p) => TYPE_LABEL[p.type] },
    {
      key: 'value',
      header: 'Valor',
      cell: (p) =>
        p.type === 'percent' ? `${p.value}%` : p.type === 'fixed' ? formatBRL(p.value) : '—',
    },
    {
      key: 'window',
      header: 'Vigência',
      cell: (p) => `${formatDate(p.starts_at)} → ${formatDate(p.ends_at)}`,
    },
    {
      key: 'usage',
      header: 'Uso',
      cell: (p) => `${p.used_count}${p.usage_limit ? ` / ${p.usage_limit}` : ''}`,
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Promoções"
        description="Cupons de desconto."
        actions={<Button onClick={openCreate}>Novo cupom</Button>}
      />

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        <DataTable
          columns={columns}
          rows={data ?? []}
          rowKey={(p) => p.id}
          emptyMessage="Nenhum cupom cadastrado."
          onRowClick={openEdit}
          rowActions={(p) => (
            <>
              <Button size="sm" variant="outline" onClick={() => openEdit(p)}>
                Editar
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setDeleteTarget(p)}>
                Excluir
              </Button>
            </>
          )}
        />
      </AsyncBoundary>

      <Modal
        open={open}
        onClose={close}
        title={editing ? `Editar cupom ${editing.code}` : 'Novo cupom'}
        size="lg"
        footer={
          <>
            <Button variant="ghost" onClick={close} disabled={saving}>
              Cancelar
            </Button>
            <Button loading={saving} onClick={() => void save()}>
              Salvar
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          {editing && (
            <Card variant="plain" className="bg-bg-subtle text-sm">
              Utilizado <strong>{editing.used_count}</strong>{' '}
              {editing.used_count === 1 ? 'vez' : 'vezes'}.
            </Card>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Código"
              required
              value={form.code}
              onChange={(e) => set('code', e.target.value.toUpperCase())}
            />
            <Select
              label="Tipo"
              value={form.type}
              options={[
                { value: 'percent', label: 'Percentual (%)' },
                { value: 'fixed', label: 'Valor fixo (R$)' },
                { value: 'free_shipping', label: 'Frete grátis' },
              ]}
              onChange={(e) => set('type', e.target.value as PromotionType)}
            />
          </div>
          <Input
            label="Descrição"
            value={form.description}
            onChange={(e) => set('description', e.target.value)}
          />
          {form.type !== 'free_shipping' && (
            <Input
              label={form.type === 'percent' ? 'Percentual de desconto' : 'Valor do desconto (R$)'}
              inputMode="decimal"
              value={form.value}
              onChange={(e) => set('value', e.target.value)}
            />
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Pedido mínimo (R$)"
              inputMode="decimal"
              value={form.min_order}
              onChange={(e) => set('min_order', e.target.value)}
            />
            <Input
              label="Desconto máximo (R$)"
              inputMode="decimal"
              value={form.max_discount}
              onChange={(e) => set('max_discount', e.target.value)}
            />
            <Input
              label="Início"
              type="date"
              value={form.starts_at}
              onChange={(e) => set('starts_at', e.target.value)}
            />
            <Input
              label="Fim"
              type="date"
              value={form.ends_at}
              onChange={(e) => set('ends_at', e.target.value)}
            />
            <Input
              label="Limite de usos (total)"
              inputMode="numeric"
              value={form.usage_limit}
              onChange={(e) => set('usage_limit', e.target.value)}
            />
            <Input
              label="Limite por cliente"
              inputMode="numeric"
              value={form.usage_limit_per_user}
              onChange={(e) => set('usage_limit_per_user', e.target.value)}
            />
          </div>
          <Checkbox label="Cupom ativo" checked={form.is_active} onChange={(v) => set('is_active', v)} />
        </div>
      </Modal>

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Excluir cupom"
        description={deleteTarget ? `Excluir o cupom "${deleteTarget.code}"?` : ''}
        confirmLabel="Excluir"
        tone="danger"
        loading={deleting}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
