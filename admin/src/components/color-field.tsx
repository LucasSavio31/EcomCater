'use client';

import { Input } from '@ecom/ui';

const HEX_RE = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/;

/**
 * Campo de cor: paleta nativa (arrastável) + hex editável.
 * Componente de módulo (referência estável) para NÃO perder o foco a cada
 * dígito digitado no hex.
 */
export function ColorField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (hex: string) => void;
}) {
  const raw = String(value ?? '#000000');
  const valid = HEX_RE.test(raw);
  return (
    <div className="flex flex-col gap-1">
      <span className="text-sm font-medium">{label}</span>
      <div className="flex items-center gap-2">
        <input
          type="color"
          value={valid ? raw.slice(0, 7) : '#000000'}
          onChange={(e) => onChange(e.target.value)}
          onInput={(e) => onChange((e.target as HTMLInputElement).value)}
          className="h-10 w-14 shrink-0 cursor-pointer rounded-card border border-surface-border p-0.5"
          aria-label={`${label} — paleta`}
        />
        <Input
          value={raw}
          aria-invalid={!valid}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1"
          placeholder="#RRGGBB"
        />
      </div>
      {!valid && <span className="text-xs text-danger">Use #RRGGBB.</span>}
    </div>
  );
}
