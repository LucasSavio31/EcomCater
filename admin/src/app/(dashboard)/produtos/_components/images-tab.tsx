'use client';

import { useRef, useState } from 'react';
import { Badge, Button, Card } from '@ecom/ui';
import { Select } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { productsApi } from '@/modules/catalog/api';
import type { ProductDetail, ProductImage } from '@/modules/catalog/types';

interface Props {
  product: ProductDetail;
  onChanged: (p: ProductDetail) => void;
}

export function ImagesTab({ product, onChanged }: Props) {
  const toast = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [uploadVariant, setUploadVariant] = useState('');
  const images = [...product.images].sort((a, b) => a.position - b.position);

  const variantOptions = product.variants.map((v) => ({
    value: v.id,
    label: v.option_labels?.join(' / ') || v.sku,
  }));

  async function refresh(): Promise<void> {
    const result = await productsApi.get(product.id);
    if (result.ok) onChanged(result.data);
  }

  async function handleUpload(file: File | undefined): Promise<void> {
    if (!file) return;
    setUploading(true);
    const result = await productsApi.uploadImage(product.id, file, uploadVariant || undefined);
    setUploading(false);
    if (inputRef.current) inputRef.current.value = '';
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success('Imagem enviada.');
    await refresh();
  }

  async function persistOrder(ordered: ProductImage[], primaryId?: string): Promise<void> {
    setBusy(true);
    const result = await productsApi.reorderImages(
      product.id,
      ordered.map((i) => i.id),
      primaryId ?? ordered.find((i) => i.is_primary)?.id,
    );
    setBusy(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    await refresh();
  }

  async function move(index: number, dir: -1 | 1): Promise<void> {
    const target = index + dir;
    if (target < 0 || target >= images.length) return;
    const reordered = [...images];
    const a = reordered[index];
    const b = reordered[target];
    if (!a || !b) return;
    reordered[index] = b;
    reordered[target] = a;
    await persistOrder(reordered);
  }

  async function remove(id: string): Promise<void> {
    setBusy(true);
    const result = await productsApi.deleteImage(product.id, id);
    setBusy(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success('Imagem removida.');
    await refresh();
  }

  return (
    <Card variant="outline" className="flex flex-col gap-4">
      <h3 className="text-sm font-semibold">Imagens do produto</h3>

      <div className="flex flex-col gap-3 rounded-card border border-surface-border p-3 sm:flex-row sm:items-end">
        {variantOptions.length > 0 && (
          <Select
            label="Associar a variação (opcional)"
            value={uploadVariant}
            placeholder="Imagem geral do produto"
            options={variantOptions}
            onChange={(e) => setUploadVariant(e.target.value)}
          />
        )}
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="sr-only"
          onChange={(e) => void handleUpload(e.target.files?.[0])}
        />
        <Button size="sm" loading={uploading} onClick={() => inputRef.current?.click()}>
          Enviar imagem
        </Button>
      </div>

      {images.length === 0 && <p className="text-sm text-text-muted">Nenhuma imagem ainda.</p>}

      <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {images.map((img, index) => (
          <li key={img.id} className="flex gap-3 rounded-card border border-surface-border p-3">
            <span className="h-24 w-24 shrink-0 overflow-hidden rounded-card bg-bg-subtle">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={img.thumb_url ?? img.url} alt={img.alt ?? ''} className="h-full w-full object-cover" />
            </span>
            <div className="flex min-w-0 flex-1 flex-col gap-2">
              <div className="flex flex-wrap items-center gap-2">
                {img.is_primary ? <Badge tone="accent">Principal</Badge> : null}
                {img.variant_id && (
                  <Badge tone="neutral">
                    {product.variants.find((v) => v.id === img.variant_id)?.sku ?? 'variação'}
                  </Badge>
                )}
              </div>
              <div className="flex flex-wrap gap-1">
                <Button size="sm" variant="ghost" disabled={busy || index === 0} onClick={() => void move(index, -1)}>
                  ↑
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busy || index === images.length - 1}
                  onClick={() => void move(index, 1)}
                >
                  ↓
                </Button>
                {!img.is_primary && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={busy}
                    onClick={() => void persistOrder(images, img.id)}
                  >
                    Tornar principal
                  </Button>
                )}
                <Button size="sm" variant="ghost" disabled={busy} onClick={() => void remove(img.id)}>
                  Excluir
                </Button>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}
