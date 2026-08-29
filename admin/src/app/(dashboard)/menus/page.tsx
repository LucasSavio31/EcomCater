'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Badge, Button, Card, Input, Modal } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox, Select } from '@/components/form-controls';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { Tabs } from '@/components/tabs';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { categoriesApi } from '@/modules/catalog/api';
import { menusApi } from '@/modules/menus/api';
import type {
  Menu,
  MenuItem,
  MenuItemInput,
  MenuLinkType,
  MenuLocation,
  ResolvedMenuItem,
} from '@/modules/menus/api';

interface FlatItem {
  item: MenuItem;
  depth: number;
  siblings: MenuItem[];
  index: number;
}

function buildFlat(items: MenuItem[]): FlatItem[] {
  const byParent = new Map<string | null, MenuItem[]>();
  for (const it of items) {
    const key = it.parent_id;
    const arr = byParent.get(key) ?? [];
    arr.push(it);
    byParent.set(key, arr);
  }
  for (const arr of byParent.values()) arr.sort((a, b) => a.position - b.position);

  const out: FlatItem[] = [];
  const walk = (parent: string | null, depth: number): void => {
    const siblings = byParent.get(parent) ?? [];
    siblings.forEach((item, index) => {
      out.push({ item, depth, siblings, index });
      walk(item.id, depth + 1);
    });
  };
  walk(null, 0);
  return out;
}

interface ItemForm {
  label: string;
  link_type: MenuLinkType;
  category_id: string;
  url: string;
  is_megamenu: boolean;
  highlight: boolean;
  show_size_shortcuts: boolean;
  size_shortcut_category_id: string;
}

const EMPTY_ITEM: ItemForm = {
  label: '',
  link_type: 'category',
  category_id: '',
  url: '',
  is_megamenu: false,
  highlight: false,
  show_size_shortcuts: false,
  size_shortcut_category_id: '',
};

export default function MenusPage() {
  const toast = useToast();
  const menusRes = useResource(() => menusApi.list());
  const categoriesRes = useResource(() => categoriesApi.list());
  const [location, setLocation] = useState<MenuLocation>('header');

  const menu: Menu | undefined = useMemo(
    () => (menusRes.data ?? []).find((m) => m.location === location),
    [menusRes.data, location],
  );

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Menus" description="Editor dos menus do cabeçalho e do rodapé." />

      <Tabs
        tabs={[
          { id: 'header', label: 'Cabeçalho' },
          { id: 'footer', label: 'Rodapé' },
        ]}
        active={location}
        onChange={(id) => setLocation(id as MenuLocation)}
      >
        <AsyncBoundary
          loading={menusRes.loading || categoriesRes.loading}
          error={menusRes.error ?? categoriesRes.error}
          onRetry={() => {
            menusRes.reload();
            categoriesRes.reload();
          }}
        >
          {menu ? (
            <MenuEditor
              menu={menu}
              location={location}
              categories={(categoriesRes.data ?? []).map((c) => ({
                value: c.id,
                label: c.path ? c.path.replace(/\//g, ' › ') : c.name,
              }))}
            />
          ) : (
            <Card variant="outline" className="flex flex-col items-start gap-3">
              <p className="text-sm text-text-muted">
                Nenhum menu para “{location === 'header' ? 'cabeçalho' : 'rodapé'}” ainda.
              </p>
              <Button
                onClick={async () => {
                  const result = await menusApi.createMenu({
                    location,
                    name: location === 'header' ? 'Menu principal' : 'Rodapé',
                    position: 0,
                    is_active: true,
                  });
                  if (!result.ok) {
                    toast.error(result.error.message);
                    return;
                  }
                  toast.success('Menu criado.');
                  menusRes.reload();
                }}
              >
                Criar menu
              </Button>
            </Card>
          )}
        </AsyncBoundary>
      </Tabs>
    </div>
  );
}

function MenuEditor({
  menu,
  location,
  categories,
}: {
  menu: Menu;
  location: MenuLocation;
  categories: Array<{ value: string; label: string }>;
}) {
  const toast = useToast();
  const itemsFetcher = useCallback(() => menusApi.listItems(menu.id), [menu.id]);
  const { data, loading, error, reload } = useResource(itemsFetcher, [menu.id]);
  const preview = useResource(() => menusApi.resolved(location), [location]);

  const [editing, setEditing] = useState<MenuItem | null>(null);
  const [creating, setCreating] = useState<{ parentId: string | null } | null>(null);
  const [form, setForm] = useState<ItemForm>(EMPTY_ITEM);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<MenuItem | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [dragId, setDragId] = useState<string | null>(null);
  const [dropHint, setDropHint] = useState<{ id: string; mode: 'before' | 'child' } | null>(null);

  const flat = useMemo(() => (data ? buildFlat(data) : []), [data]);
  const open = editing !== null || creating !== null;
  const set = <K extends keyof ItemForm>(k: K, v: ItemForm[K]): void =>
    setForm((prev) => ({ ...prev, [k]: v }));

  useEffect(() => {
    if (editing) {
      setForm({
        label: editing.label,
        link_type: editing.link_type,
        category_id: editing.category_id ?? '',
        url: editing.url ?? '',
        is_megamenu: editing.is_megamenu,
        highlight: editing.highlight,
        show_size_shortcuts: editing.show_size_shortcuts,
        size_shortcut_category_id: editing.size_shortcut_category_id ?? '',
      });
    } else if (creating) {
      setForm(EMPTY_ITEM);
    }
  }, [editing, creating]);

  function refresh(): void {
    reload();
    preview.reload();
  }

  async function reorder(item: FlatItem, dir: -1 | 1): Promise<void> {
    const target = item.index + dir;
    if (target < 0 || target >= item.siblings.length) return;
    const ordered = [...item.siblings];
    const a = ordered[item.index];
    const b = ordered[target];
    if (!a || !b) return;
    ordered[item.index] = b;
    ordered[target] = a;
    const result = await menusApi.reorderItems(
      ordered.map((n, position) => ({ id: n.id, position, parent_id: n.parent_id })),
    );
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    refresh();
  }

  /** Reordena/aninha por arrastar-e-soltar. `mode` 'child' aninha em `targetId`;
   * 'before' insere como irmão logo antes de `targetId`. */
  async function dndReorder(sourceId: string, targetId: string, mode: 'before' | 'child'): Promise<void> {
    if (!data || sourceId === targetId) return;
    const byId = new Map(data.map((i) => [i.id, i]));
    // impede soltar dentro da própria subárvore
    const isDescendant = (candidate: string): boolean => {
      let cur = byId.get(candidate)?.parent_id ?? null;
      while (cur) {
        if (cur === sourceId) return true;
        cur = byId.get(cur)?.parent_id ?? null;
      }
      return false;
    };
    if (targetId === sourceId || isDescendant(targetId)) return;

    const target = byId.get(targetId);
    if (!target) return;
    const newParent = mode === 'child' ? targetId : target.parent_id;

    // reconstrói a lista de filhos de cada pai, movendo o item
    const children = new Map<string | null, MenuItem[]>();
    for (const it of data) {
      const key = it.id === sourceId ? '__moved__' : it.parent_id;
      if (key === '__moved__') continue;
      const arr = children.get(key) ?? [];
      arr.push(it);
      children.set(key, arr);
    }
    for (const arr of children.values()) arr.sort((a, b) => a.position - b.position);

    const moved = byId.get(sourceId)!;
    const destArr = children.get(newParent) ?? [];
    if (mode === 'child') {
      destArr.push(moved);
    } else {
      const idx = destArr.findIndex((c) => c.id === targetId);
      destArr.splice(idx < 0 ? destArr.length : idx, 0, moved);
    }
    children.set(newParent, destArr);

    // emite a lista completa com posições recalculadas e parent atualizado
    const payload: Array<{ id: string; position: number; parent_id: string | null }> = [];
    for (const [parent, arr] of children.entries()) {
      arr.forEach((it, position) => {
        payload.push({
          id: it.id,
          position,
          parent_id: it.id === sourceId ? newParent : parent,
        });
      });
    }
    const result = await menusApi.reorderItems(payload);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    refresh();
  }

  function buildPayload(): MenuItemInput {
    return {
      label: form.label.trim(),
      link_type: form.link_type,
      category_id: form.link_type === 'category' ? form.category_id || null : null,
      url: form.link_type === 'url' ? form.url.trim() || null : null,
      position: editing ? editing.position : (data?.filter((i) => i.parent_id === (creating?.parentId ?? null)).length ?? 0),
      parent_id: editing ? editing.parent_id : creating?.parentId ?? null,
      is_megamenu: form.is_megamenu,
      highlight: form.highlight,
      show_size_shortcuts: form.show_size_shortcuts,
      size_shortcut_category_id: form.show_size_shortcuts ? form.size_shortcut_category_id || null : null,
    };
  }

  async function save(): Promise<void> {
    if (!form.label.trim()) {
      toast.error('Informe o rótulo do item.');
      return;
    }
    setSaving(true);
    const payload = buildPayload();
    const result = editing
      ? await menusApi.updateItem(editing.id, payload)
      : await menusApi.createItem(menu.id, payload);
    setSaving(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success(editing ? 'Item salvo.' : 'Item adicionado.');
    setEditing(null);
    setCreating(null);
    refresh();
  }

  async function confirmDelete(): Promise<void> {
    if (!deleteTarget) return;
    setDeleting(true);
    const result = await menusApi.deleteItem(deleteTarget.id);
    setDeleting(false);
    if (!result.ok) {
      toast.error(result.error.message);
      setDeleteTarget(null);
      return;
    }
    toast.success('Item removido.');
    setDeleteTarget(null);
    refresh();
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
      <Card variant="outline" className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Itens</h2>
          <Button size="sm" onClick={() => setCreating({ parentId: null })}>
            Adicionar item
          </Button>
        </div>
        <p className="text-xs text-text-muted">
          Arraste um item para reordenar. Solte <strong>sobre</strong> outro item para transformá-lo em
          subitem; solte na <strong>metade de cima</strong> para inseri-lo antes. As setas ↑ ↓ fazem o
          mesmo pelo teclado.
        </p>

        <AsyncBoundary
          loading={loading}
          error={error}
          onRetry={reload}
          empty={flat.length === 0}
          emptyMessage="Nenhum item no menu."
        >
          <ul className="flex flex-col gap-1">
            {flat.map((row) => {
              const hint = dropHint?.id === row.item.id ? dropHint.mode : null;
              return (
                <li
                  key={row.item.id}
                  draggable
                  onDragStart={(e) => {
                    setDragId(row.item.id);
                    e.dataTransfer.effectAllowed = 'move';
                  }}
                  onDragEnd={() => {
                    setDragId(null);
                    setDropHint(null);
                  }}
                  onDragOver={(e) => {
                    if (!dragId || dragId === row.item.id) return;
                    e.preventDefault();
                    const rect = e.currentTarget.getBoundingClientRect();
                    const mode = e.clientY - rect.top < rect.height / 2 ? 'before' : 'child';
                    setDropHint({ id: row.item.id, mode });
                  }}
                  onDragLeave={() => setDropHint((h) => (h?.id === row.item.id ? null : h))}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (dragId && dropHint?.id === row.item.id) {
                      void dndReorder(dragId, row.item.id, dropHint.mode);
                    }
                    setDragId(null);
                    setDropHint(null);
                  }}
                  className={[
                    'flex items-center gap-1 rounded-card px-2 py-1.5 text-sm hover:bg-bg-subtle',
                    dragId === row.item.id ? 'opacity-40' : '',
                    hint === 'before' ? 'border-t-2 border-accent' : '',
                    hint === 'child' ? 'ring-2 ring-accent ring-inset bg-bg-subtle' : '',
                  ].join(' ')}
                  style={{ marginLeft: `${row.depth * 1.25}rem` }}
                >
                  <span aria-hidden className="cursor-grab select-none px-1 text-text-muted">⠿</span>
                  <button type="button" className="flex-1 truncate text-left" onClick={() => setEditing(row.item)}>
                    {row.item.label}
                    <span className="ml-2 text-xs text-text-muted">{row.item.link_type}</span>
                    {row.item.is_megamenu && <Badge tone="accent" className="ml-1">mega</Badge>}
                    {row.item.highlight && <Badge tone="warning" className="ml-1">destaque</Badge>}
                  </button>
                  <button
                    type="button"
                    aria-label="Mover para cima"
                    disabled={row.index === 0}
                    className="min-h-touch w-6 text-text-muted disabled:opacity-30"
                    onClick={() => void reorder(row, -1)}
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    aria-label="Mover para baixo"
                    disabled={row.index === row.siblings.length - 1}
                    className="min-h-touch w-6 text-text-muted disabled:opacity-30"
                    onClick={() => void reorder(row, 1)}
                  >
                    ↓
                  </button>
                  <button
                    type="button"
                    aria-label="Adicionar subitem"
                    className="min-h-touch w-6 text-text-muted"
                    onClick={() => setCreating({ parentId: row.item.id })}
                  >
                    +
                  </button>
                  <button
                    type="button"
                    aria-label="Remover"
                    className="min-h-touch w-6 text-text-muted hover:text-danger"
                    onClick={() => setDeleteTarget(row.item)}
                  >
                    ×
                  </button>
                </li>
              );
            })}
          </ul>
        </AsyncBoundary>
      </Card>

      <Card variant="outline" className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Pré-visualização</h2>
        <AsyncBoundary loading={preview.loading} error={preview.error} onRetry={preview.reload}>
          <PreviewTree items={preview.data?.items ?? []} />
        </AsyncBoundary>
      </Card>

      <Modal
        open={open}
        onClose={() => {
          setEditing(null);
          setCreating(null);
        }}
        title={editing ? 'Editar item' : 'Novo item'}
        size="md"
        footer={
          <>
            <Button
              variant="ghost"
              disabled={saving}
              onClick={() => {
                setEditing(null);
                setCreating(null);
              }}
            >
              Cancelar
            </Button>
            <Button loading={saving} onClick={() => void save()}>
              Salvar
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          <Input label="Rótulo" required value={form.label} onChange={(e) => set('label', e.target.value)} />
          <Select
            label="Tipo de link"
            value={form.link_type}
            options={[
              { value: 'category', label: 'Categoria' },
              { value: 'url', label: 'URL' },
              { value: 'page', label: 'Página institucional' },
            ]}
            onChange={(e) => set('link_type', e.target.value as MenuLinkType)}
          />
          {form.link_type === 'category' && (
            <Select
              label="Categoria"
              value={form.category_id}
              placeholder="Selecione"
              options={categories}
              onChange={(e) => set('category_id', e.target.value)}
            />
          )}
          {form.link_type === 'url' && (
            <Input label="URL" value={form.url} onChange={(e) => set('url', e.target.value)} placeholder="/ofertas" />
          )}
          <div className="flex flex-col gap-2 rounded-card border border-surface-border p-3">
            <Checkbox label="Mega menu (dropdown rico)" checked={form.is_megamenu} onChange={(v) => set('is_megamenu', v)} />
            <Checkbox label="Destaque (ex.: “ATÉ 50% OFF”)" checked={form.highlight} onChange={(v) => set('highlight', v)} />
            <Checkbox
              label="Mostrar atalhos “compre por tamanho”"
              checked={form.show_size_shortcuts}
              onChange={(v) => set('show_size_shortcuts', v)}
            />
            {form.show_size_shortcuts && (
              <Select
                label="Categoria dos atalhos de tamanho"
                value={form.size_shortcut_category_id}
                placeholder="Selecione"
                options={categories}
                onChange={(e) => set('size_shortcut_category_id', e.target.value)}
              />
            )}
          </div>
        </div>
      </Modal>

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Remover item do menu"
        description={deleteTarget ? `Remover "${deleteTarget.label}" e seus subitens?` : ''}
        confirmLabel="Remover"
        tone="danger"
        loading={deleting}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}

function PreviewTree({ items }: { items: ResolvedMenuItem[] }) {
  if (items.length === 0) return <p className="text-sm text-text-muted">Menu vazio.</p>;
  return (
    <ul className="flex flex-col gap-1 text-sm">
      {items.map((it) => (
        <li key={it.id}>
          <span className="font-medium">{it.label}</span>
          {it.resolved_url && <span className="ml-2 text-xs text-text-muted">{it.resolved_url}</span>}
          {it.children.length > 0 && (
            <ul className="ml-4 mt-1 flex flex-col gap-1 border-l border-surface-border pl-3">
              {it.children.map((c) => (
                <li key={c.id}>
                  {c.label}
                  {c.resolved_url && <span className="ml-2 text-xs text-text-muted">{c.resolved_url}</span>}
                </li>
              ))}
            </ul>
          )}
        </li>
      ))}
    </ul>
  );
}
