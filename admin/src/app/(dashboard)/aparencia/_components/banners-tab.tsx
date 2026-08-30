'use client';

import { useState } from 'react';
import { Badge, Button, Card, Input, Modal } from '@ecom/ui';
import { Checkbox, Select } from '@/components/form-controls';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { ImageUploader } from '@/components/image-uploader';
import { AsyncBoundary } from '@/components/async-boundary';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { formatDate } from '@/lib/format';
import {
  appearanceApi,
  uploadBannerImage,
  type Banner,
  type BannerInput,
} from '@/modules/appearance/api';

interface FormState {
  slot: string;
  title: string;
  link_url: string;
  alt: string;
  position: string;
  starts_at: string;
  ends_at: string;
  is_active: boolean;
}

const EMPTY: FormState = {
  slot: 'hero',
  title: '',
  link_url: '',
  alt: '',
  position: '0',
  starts_at: '',
  ends_at: '',
  is_active: true,
};

export function BannersTab() {
  const toast = useToast();
  const { data, loading, error, reload } = useResource(() => appearanceApi.listBanners());

  const [editing, setEditing] = useState<Banner | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Banner | null>(null);
  const [deleting, setDeleting] = useState(false);

  const open = creating || editing !== null;
  const set = <K extends keyof FormState>(k: K, v: FormState[K]): void =>
    setForm((prev) => ({ ...prev, [k]: v }));

  function openCreate(): void {
    setForm(EMPTY);
    setEditing(null);
    setCreating(true);
  }
  function openEdit(b: Banner): void {
    setForm({
      slot: b.slot,
      title: b.title ?? '',
      link_url: b.link_url ?? '',
      alt: b.alt ?? '',
      position: String(b.position),
      starts_at: b.starts_at ? b.starts_at.slice(0, 10) : '',
      ends_at: b.ends_at ? b.ends_at.slice(0, 10) : '',
      is_active: b.is_active,
    });
    setCreating(false);
    setEditing(b);
  }
  function close(): void {
    setCreating(false);
    setEditing(null);
  }

  function payload(): BannerInput {
    return {
      slot: form.slot.trim() || 'hero',
      title: form.title.trim() || null,
      link_url: form.link_url.trim() || null,
      alt: form.alt.trim() || null,
      position: Number(form.position) || 0,
      starts_at: form.starts_at ? new Date(form.starts_at).toISOString() : null,
      ends_at: form.ends_at ? new Date(form.ends_at).toISOString() : null,
      is_active: form.is_active,
    };
  }

  async function save(): Promise<void> {
    setSaving(true);
    const result = editing
      ? await appearanceApi.updateBanner(editing.id, payload())
      : await appearanceApi.createBanner(payload());
    setSaving(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success(editing ? 'Banner salvo.' : 'Banner criado.');
    if (!editing) setEditing(result.data);
    setCreating(false);
    reload();
  }

  async function confirmDelete(): Promise<void> {
    if (!deleteTarget) return;
    setDeleting(true);
    const result = await appearanceApi.deleteBanner(deleteTarget.id);
    setDeleting(false);
    if (!result.ok) {
      toast.error(result.error.message);
      setDeleteTarget(null);
      return;
    }
    toast.success('Banner excluído.');
    setDeleteTarget(null);
    reload();
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-text-muted">Banners da home, agrupados por slot.</p>
        <Button onClick={openCreate}>Novo banner</Button>
      </div>

      <AsyncBoundary
        loading={loading}
        error={error}
        onRetry={reload}
        empty={(data?.length ?? 0) === 0}
        emptyMessage="Nenhum banner."
      >
        <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {(data ?? [])
            .slice()
            .sort((a, b) => a.slot.localeCompare(b.slot) || a.position - b.position)
            .map((b) => (
              <li key={b.id}>
                <Card variant="outline" className="flex flex-col gap-2">
                  <div className="flex items-center justify-between gap-2">
                    <Badge tone="neutral">{b.slot}</Badge>
                    {b.is_active ? <Badge tone="success">ativo</Badge> : <Badge tone="neutral">inativo</Badge>}
                  </div>
                  <div className="h-24 overflow-hidden rounded-card bg-bg-subtle">
                    {(b.image_url ?? b.image_desktop_url) && (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={b.image_url ?? b.image_desktop_url ?? ''}
                        alt={b.alt ?? ''}
                        className="h-full w-full object-cover"
                      />
                    )}
                  </div>
                  <p className="text-sm font-medium">{b.title ?? '(sem título)'}</p>
                  <p className="text-xs text-text-muted">
                    {formatDate(b.starts_at)} → {formatDate(b.ends_at)} · pos {b.position}
                  </p>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => openEdit(b)}>
                      Editar
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setDeleteTarget(b)}>
                      Excluir
                    </Button>
                  </div>
                </Card>
              </li>
            ))}
        </ul>
      </AsyncBoundary>

      <Modal
        open={open}
        onClose={close}
        title={editing ? 'Editar banner' : 'Novo banner'}
        size="lg"
        footer={
          <>
            <Button variant="ghost" onClick={close} disabled={saving}>
              Fechar
            </Button>
            <Button loading={saving} onClick={() => void save()}>
              Salvar dados
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Select
              label="Tipo de banner (slot)"
              value={form.slot}
              onChange={(e) => set('slot', e.target.value)}
              options={[
                { value: 'hero', label: 'Hero (banner principal da home)' },
                { value: 'showcase', label: 'Showcase (faixa/vitrine da home)' },
                { value: 'top_bar', label: 'Top bar (tarja acima do menu)' },
              ]}
            />
            <Input label="Posição" inputMode="numeric" value={form.position} onChange={(e) => set('position', e.target.value)} />
            <Input label="Título" value={form.title} onChange={(e) => set('title', e.target.value)} />
            <Input label="Texto alternativo" value={form.alt} onChange={(e) => set('alt', e.target.value)} />
            <Input label="Link" value={form.link_url} onChange={(e) => set('link_url', e.target.value)} />
            <Input label="Início" type="date" value={form.starts_at} onChange={(e) => set('starts_at', e.target.value)} />
            <Input label="Fim" type="date" value={form.ends_at} onChange={(e) => set('ends_at', e.target.value)} />
          </div>
          <Checkbox label="Ativo" checked={form.is_active} onChange={(v) => set('is_active', v)} />

          {editing ? (
            <div className="flex flex-col gap-2 border-t border-surface-border pt-4">
              <ImageUploader
                label="Imagem"
                aspect="wide"
                currentUrl={editing.image_url ?? editing.image_desktop_url}
                hint="Uma imagem só — ela é redimensionada automaticamente para desktop e mobile."
                onSelect={async (file) => {
                  const r = await uploadBannerImage(editing.id, file);
                  if (!r.ok) throw new Error(r.error.message);
                  setEditing(r.data);
                  reload();
                  toast.success('Imagem enviada.');
                }}
              />
            </div>
          ) : (
            <p className="text-sm text-text-muted">Salve o banner para enviar a imagem.</p>
          )}
        </div>
      </Modal>

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Excluir banner"
        description={deleteTarget ? `Excluir o banner "${deleteTarget.title ?? deleteTarget.slot}"?` : ''}
        confirmLabel="Excluir"
        tone="danger"
        loading={deleting}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
