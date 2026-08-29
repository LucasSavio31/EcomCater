'use client';

import { useId, useRef, useState } from 'react';
import { Button, cn } from '@ecom/ui';

interface ImageUploaderProps {
  /** URL da imagem já salva (preview inicial). */
  currentUrl?: string | null;
  label?: string;
  hint?: string;
  /** Recebe o arquivo escolhido; deve fazer o upload e devolver quando terminar. */
  onSelect: (file: File) => Promise<void>;
  onRemove?: () => Promise<void>;
  disabled?: boolean;
  /** Proporção do quadro de preview. */
  aspect?: 'square' | 'wide';
}

export function ImageUploader({
  currentUrl,
  label = 'Imagem',
  hint,
  onSelect,
  onRemove,
  disabled = false,
  aspect = 'square',
}: ImageUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const fieldId = useId();
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const shown = preview ?? currentUrl ?? null;

  async function handleFile(file: File | undefined): Promise<void> {
    if (!file) return;
    setError(null);
    if (!file.type.startsWith('image/')) {
      setError('Selecione um arquivo de imagem.');
      return;
    }
    const localUrl = URL.createObjectURL(file);
    setPreview(localUrl);
    setBusy(true);
    try {
      await onSelect(file);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha no upload.');
      setPreview(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm font-medium text-text">{label}</span>
      <div
        className={cn(
          'flex items-center justify-center overflow-hidden rounded-card border border-dashed border-surface-border bg-bg-subtle',
          aspect === 'square' ? 'h-40 w-40' : 'h-32 w-full max-w-md',
        )}
      >
        {shown ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={shown} alt="" className="h-full w-full object-contain" />
        ) : (
          <span className="px-3 text-center text-xs text-text-muted">Nenhuma imagem</span>
        )}
      </div>
      <input
        ref={inputRef}
        id={fieldId}
        type="file"
        accept="image/*"
        className="sr-only"
        disabled={disabled || busy}
        onChange={(e) => void handleFile(e.target.files?.[0])}
      />
      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={disabled || busy}
          loading={busy}
          onClick={() => inputRef.current?.click()}
        >
          {shown ? 'Trocar' : 'Enviar'}
        </Button>
        {shown && onRemove && (
          <Button
            variant="ghost"
            size="sm"
            disabled={disabled || busy}
            onClick={async () => {
              setBusy(true);
              try {
                await onRemove();
                setPreview(null);
              } finally {
                setBusy(false);
              }
            }}
          >
            Remover
          </Button>
        )}
      </div>
      {hint && !error && <p className="text-xs text-text-muted">{hint}</p>}
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  );
}
