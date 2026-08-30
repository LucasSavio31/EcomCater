'use client';

import { useState } from 'react';
import { Badge, Button, Card, Input } from '@ecom/ui';
import { Checkbox, Textarea } from '@/components/form-controls';
import { RichTextarea } from '@/components/rich-textarea';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { AsyncBoundary } from '@/components/async-boundary';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { slugify } from '@/lib/format';
import { appearanceApi, type ContentPage, type ContentPageInput } from '@/modules/appearance/api';

interface FormState {
  title: string;
  slug: string;
  body: string;
  is_published: boolean;
  seo_title: string;
  seo_description: string;
}

const EMPTY: FormState = {
  title: '',
  slug: '',
  body: '',
  is_published: false,
  seo_title: '',
  seo_description: '',
};

export function PagesTab() {
  const toast = useToast();
  const { data, loading, error, reload } = useResource(() => appearanceApi.listPages());

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ContentPage | null>(null);
  const [deleting, setDeleting] = useState(false);

  const set = <K extends keyof FormState>(k: K, v: FormState[K]): void =>
    setForm((prev) => ({ ...prev, [k]: v }));

  function startNew(): void {
    setSelectedId(null);
    setForm(EMPTY);
  }
  function startEdit(p: ContentPage): void {
    setSelectedId(p.id);
    setForm({
      title: p.title,
      slug: p.slug,
      body: p.body,
      is_published: p.is_published,
      seo_title: p.seo_title ?? '',
      seo_description: p.seo_description ?? '',
    });
  }

  async function save(): Promise<void> {
    if (!form.title.trim()) {
      toast.error('Informe o título.');
      return;
    }
    const payload: ContentPageInput = {
      title: form.title.trim(),
      slug: (form.slug.trim() || slugify(form.title)) || undefined,
      body: form.body,
      is_published: form.is_published,
      seo_title: form.seo_title.trim() || null,
      seo_description: form.seo_description.trim() || null,
    };
    setSaving(true);
    const result = selectedId
      ? await appearanceApi.updatePage(selectedId, payload)
      : await appearanceApi.createPage(payload);
    setSaving(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success(selectedId ? 'Página salva.' : 'Página criada.');
    setSelectedId(result.data.id);
    reload();
  }

  async function confirmDelete(): Promise<void> {
    if (!deleteTarget) return;
    setDeleting(true);
    const result = await appearanceApi.deletePage(deleteTarget.id);
    setDeleting(false);
    if (!result.ok) {
      toast.error(result.error.message);
      setDeleteTarget(null);
      return;
    }
    toast.success('Página excluída.');
    if (selectedId === deleteTarget.id) startNew();
    setDeleteTarget(null);
    reload();
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1.6fr]">
      <Card variant="outline" className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Páginas</h2>
          <Button size="sm" onClick={startNew}>
            Nova
          </Button>
        </div>
        <AsyncBoundary
          loading={loading}
          error={error}
          onRetry={reload}
          empty={(data?.length ?? 0) === 0}
          emptyMessage="Nenhuma página."
        >
          <ul className="flex flex-col gap-1">
            {(data ?? []).map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => startEdit(p)}
                  className={[
                    'flex w-full items-center justify-between rounded-card px-2 py-1.5 text-left text-sm',
                    selectedId === p.id ? 'bg-bg-subtle' : 'hover:bg-bg-subtle',
                  ].join(' ')}
                >
                  <span className="truncate">{p.title}</span>
                  {p.is_published ? <Badge tone="success">pub</Badge> : <Badge tone="neutral">rascunho</Badge>}
                </button>
              </li>
            ))}
          </ul>
        </AsyncBoundary>
      </Card>

      <Card variant="outline" className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold">{selectedId ? 'Editar página' : 'Nova página'}</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Input label="Título" required value={form.title} onChange={(e) => set('title', e.target.value)} />
          <Input
            label="Slug"
            value={form.slug}
            onChange={(e) => set('slug', e.target.value)}
            placeholder={slugify(form.title) || 'gerado do título'}
          />
        </div>
        <RichTextarea
          label="Conteúdo"
          value={form.body}
          onChange={(v) => set('body', v)}
          hint="Escreva normalmente e formate pela barra (negrito, título, lista, link, fonte, tamanho)."
        />
        <Checkbox label="Publicada" checked={form.is_published} onChange={(v) => set('is_published', v)} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Input label="Título SEO" value={form.seo_title} onChange={(e) => set('seo_title', e.target.value)} />
          <Textarea
            label="Descrição SEO"
            rows={2}
            value={form.seo_description}
            onChange={(e) => set('seo_description', e.target.value)}
          />
        </div>
        <div className="flex gap-2">
          <Button loading={saving} onClick={() => void save()}>
            {selectedId ? 'Salvar' : 'Criar'}
          </Button>
          {selectedId && (
            <Button variant="ghost" onClick={() => setDeleteTarget((data ?? []).find((p) => p.id === selectedId) ?? null)}>
              Excluir
            </Button>
          )}
        </div>
      </Card>

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Excluir página"
        description={deleteTarget ? `Excluir "${deleteTarget.title}"?` : ''}
        confirmLabel="Excluir"
        tone="danger"
        loading={deleting}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
