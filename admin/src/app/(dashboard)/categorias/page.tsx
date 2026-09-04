'use client';

import { useCallback, useMemo, useState } from 'react';
import { Button, Card, Input, Tooltip } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox, Select, Textarea } from '@/components/form-controls';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { ImageUploader } from '@/components/image-uploader';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { slugify } from '@/lib/format';
import { categoriesApi } from '@/modules/catalog/api';
import type { Category, CategoryTreeNode } from '@/modules/catalog/types';

interface FlatNode {
  node: CategoryTreeNode;
  depth: number;
  siblings: CategoryTreeNode[];
  index: number;
}

function flatten(
  nodes: CategoryTreeNode[],
  expanded: Set<string>,
  depth = 0,
  out: FlatNode[] = [],
): FlatNode[] {
  nodes.forEach((node, index) => {
    out.push({ node, depth, siblings: nodes, index });
    if (node.children.length > 0 && expanded.has(node.id)) {
      flatten(node.children, expanded, depth + 1, out);
    }
  });
  return out;
}

interface FormState {
  name: string;
  parent_id: string;
  description: string;
  is_active: boolean;
  seo_title: string;
  seo_description: string;
}

const EMPTY_FORM: FormState = {
  name: '',
  parent_id: '',
  description: '',
  is_active: true,
  seo_title: '',
  seo_description: '',
};

export default function CategoriasPage() {
  const toast = useToast();
  const { data, loading, error, reload } = useResource(() => categoriesApi.tree());
  const flatList = useResource(() => categoriesApi.list());

  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Category | null>(null);
  const [deleting, setDeleting] = useState(false);

  const rows = useMemo(() => (data ? flatten(data, expanded) : []), [data, expanded]);
  const allCategories = flatList.data ?? [];
  const selected = allCategories.find((c) => c.id === selectedId) ?? null;

  const set = <K extends keyof FormState>(key: K, value: FormState[K]): void =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const startNew = useCallback((parentId?: string) => {
    setSelectedId(null);
    setForm({ ...EMPTY_FORM, parent_id: parentId ?? '' });
  }, []);

  const startEdit = useCallback(
    (cat: Category) => {
      setSelectedId(cat.id);
      setForm({
        name: cat.name,
        parent_id: cat.parent_id ?? '',
        description: cat.description ?? '',
        is_active: cat.is_active,
        seo_title: cat.seo_title ?? '',
        seo_description: cat.seo_description ?? '',
      });
    },
    [],
  );

  function toggle(id: string): void {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function refreshAll(): void {
    reload();
    flatList.reload();
  }

  async function reorderSiblings(item: FlatNode, dir: -1 | 1): Promise<void> {
    const target = item.index + dir;
    if (target < 0 || target >= item.siblings.length) return;
    const ordered = [...item.siblings];
    const a = ordered[item.index];
    const b = ordered[target];
    if (!a || !b) return;
    ordered[item.index] = b;
    ordered[target] = a;
    const result = await categoriesApi.reorder(
      ordered.map((n, position) => ({ id: n.id, position, parent_id: n.parent_id })),
    );
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    refreshAll();
  }

  async function submit(): Promise<void> {
    if (!form.name.trim()) {
      toast.error('Informe o nome da categoria.');
      return;
    }
    setSaving(true);
    const body = {
      name: form.name.trim(),
      parent_id: form.parent_id || null,
      description: form.description.trim() || null,
      is_active: form.is_active,
      seo_title: form.seo_title.trim() || null,
      seo_description: form.seo_description.trim() || null,
    };
    const result = selectedId
      ? await categoriesApi.update(selectedId, body)
      : await categoriesApi.create(body);
    setSaving(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success(selectedId ? 'Categoria salva.' : 'Categoria criada.');
    setSelectedId(result.data.id);
    refreshAll();
  }

  async function confirmDelete(): Promise<void> {
    if (!deleteTarget) return;
    setDeleting(true);
    const result = await categoriesApi.remove(deleteTarget.id);
    setDeleting(false);
    if (!result.ok) {
      if (result.error.status === 409) {
        toast.error('Não é possível excluir: a categoria tem subcategorias ou produtos vinculados.');
      } else {
        toast.error(result.error.message);
      }
      setDeleteTarget(null);
      return;
    }
    toast.success('Categoria excluída.');
    if (selectedId === deleteTarget.id) startNew();
    setDeleteTarget(null);
    refreshAll();
  }

  const parentOptions = allCategories
    .filter((c) => c.id !== selectedId)
    .map((c) => ({ value: c.id, label: c.path ? c.path.replace(/\//g, ' › ') : c.name }));

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Categorias"
        description="Árvore de categorias da loja."
        actions={<Button onClick={() => startNew()}>Nova categoria</Button>}
      />

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card variant="outline" className="flex flex-col gap-1">
          <AsyncBoundary
            loading={loading}
            error={error}
            onRetry={reload}
            empty={rows.length === 0}
            emptyMessage="Nenhuma categoria cadastrada."
          >
            <ul className="flex flex-col gap-1">
              {rows.map((item) => (
                <li
                  key={item.node.id}
                  className={[
                    'flex items-center gap-1 rounded-card px-2 py-1.5 text-sm',
                    selectedId === item.node.id ? 'bg-bg-subtle' : 'hover:bg-bg-subtle',
                  ].join(' ')}
                  style={{ paddingLeft: `${item.depth * 1.25 + 0.5}rem` }}
                >
                  {item.node.children.length > 0 ? (
                    <Tooltip label={expanded.has(item.node.id) ? 'Colapsar' : 'Expandir'}>
                      <button
                        type="button"
                        aria-label={expanded.has(item.node.id) ? 'Colapsar' : 'Expandir'}
                        aria-expanded={expanded.has(item.node.id)}
                        className="min-h-touch w-6 shrink-0 text-text-muted"
                        onClick={() => toggle(item.node.id)}
                      >
                        {expanded.has(item.node.id) ? '▾' : '▸'}
                      </button>
                    </Tooltip>
                  ) : (
                    <span className="w-6 shrink-0" />
                  )}
                  <button
                    type="button"
                    className="flex-1 truncate text-left"
                    onClick={() => startEdit(item.node)}
                  >
                    {item.node.name}
                    {!item.node.is_active && <span className="ml-2 text-xs text-text-muted">(inativa)</span>}
                  </button>
                  <span className="hidden text-xs text-text-muted sm:inline">
                    {item.node.product_count ?? 0} prod.
                  </span>
                  <Tooltip label="Mover para cima">
                    <button
                      type="button"
                      aria-label="Mover para cima"
                      disabled={item.index === 0}
                      className="min-h-touch w-6 text-text-muted disabled:opacity-30"
                      onClick={() => void reorderSiblings(item, -1)}
                    >
                      ↑
                    </button>
                  </Tooltip>
                  <Tooltip label="Mover para baixo">
                    <button
                      type="button"
                      aria-label="Mover para baixo"
                      disabled={item.index === item.siblings.length - 1}
                      className="min-h-touch w-6 text-text-muted disabled:opacity-30"
                      onClick={() => void reorderSiblings(item, 1)}
                    >
                      ↓
                    </button>
                  </Tooltip>
                  <Tooltip label="Adicionar subcategoria">
                    <button
                      type="button"
                      aria-label="Adicionar subcategoria"
                      className="min-h-touch w-6 text-text-muted"
                      onClick={() => startNew(item.node.id)}
                    >
                      +
                    </button>
                  </Tooltip>
                  <Tooltip label="Excluir">
                    <button
                      type="button"
                      aria-label="Excluir"
                      className="min-h-touch w-6 text-text-muted hover:text-danger"
                      onClick={() => setDeleteTarget(item.node)}
                    >
                      ×
                    </button>
                  </Tooltip>
                </li>
              ))}
            </ul>
          </AsyncBoundary>
        </Card>

        <Card variant="outline" className="flex flex-col gap-4">
          <h2 className="text-lg font-semibold">{selectedId ? 'Editar categoria' : 'Nova categoria'}</h2>
          <Input
            label="Nome"
            required
            value={form.name}
            onChange={(e) => set('name', e.target.value)}
            hint={form.name ? `slug: ${slugify(form.name)}` : undefined}
          />
          <Select
            label="Categoria pai"
            value={form.parent_id}
            placeholder="Raiz (sem pai)"
            options={parentOptions}
            onChange={(e) => set('parent_id', e.target.value)}
          />
          <Textarea
            label="Descrição"
            value={form.description}
            onChange={(e) => set('description', e.target.value)}
            rows={3}
          />
          <Checkbox label="Ativa" checked={form.is_active} onChange={(v) => set('is_active', v)} />

          {selected && (
            <ImageUploader
              label="Imagem da categoria"
              currentUrl={selected.image_url ?? null}
              aspect="wide"
              onSelect={async (file) => {
                const result = await categoriesApi.uploadImage(selected.id, file);
                if (!result.ok) throw new Error(result.error.message);
                toast.success('Imagem atualizada.');
                refreshAll();
              }}
            />
          )}

          <Input
            label="Título SEO"
            value={form.seo_title}
            onChange={(e) => set('seo_title', e.target.value)}
          />
          <Textarea
            label="Descrição SEO"
            value={form.seo_description}
            onChange={(e) => set('seo_description', e.target.value)}
            rows={2}
          />

          <div className="flex gap-2">
            <Button loading={saving} onClick={() => void submit()}>
              {selectedId ? 'Salvar' : 'Criar'}
            </Button>
            {selectedId && (
              <Button variant="ghost" onClick={() => startNew()}>
                Cancelar
              </Button>
            )}
          </div>
        </Card>
      </div>

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Excluir categoria"
        description={
          deleteTarget
            ? `Tem certeza que deseja excluir "${deleteTarget.name}"? Categorias com subcategorias ou produtos não podem ser excluídas.`
            : ''
        }
        confirmLabel="Excluir"
        tone="danger"
        loading={deleting}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
