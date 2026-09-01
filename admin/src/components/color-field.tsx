'use client';

import { memo, useEffect, useRef, useState } from 'react';
import { Input } from '@ecom/ui';

const HEX_RE = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/;

interface ColorFieldProps {
  label: string;
  value: string;
  onChange: (hex: string) => void;
  /** Atraso antes de propagar a mudança para o editor do tema (ms). */
  commitDelayMs?: number;
}

/**
 * Campo de cor: paleta nativa (arrastável) + hex editável.
 *
 * Guarda um rascunho local e só propaga para o `useThemeEditor` de forma
 * "debounced" (e no blur). Assim, arrastar a paleta re-renderiza só este
 * componente em tempo real; a aba inteira re-renderiza no máximo a cada
 * `commitDelayMs` — e os demais campos, memoizados, nem re-renderizam.
 */
function ColorFieldImpl({ label, value, onChange, commitDelayMs = 120 }: ColorFieldProps) {
  const initial = String(value ?? '#000000');
  const [local, setLocal] = useState(initial);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latest = useRef(local);
  latest.current = local;
  // Último valor que já enviamos ao pai (ou que veio do pai). Serve para
  // distinguir "mudou de fora" (salvar/descartar) de "eco da minha edição".
  const committed = useRef(initial);

  useEffect(() => {
    const incoming = String(value ?? '#000000');
    if (incoming !== committed.current) {
      committed.current = incoming;
      setLocal(incoming);
    }
  }, [value]);

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  const scheduleCommit = (hex: string): void => {
    setLocal(hex);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      committed.current = hex;
      onChange(hex);
    }, commitDelayMs);
  };

  const commitNow = (): void => {
    if (timer.current) clearTimeout(timer.current);
    if (latest.current !== committed.current) {
      committed.current = latest.current;
      onChange(latest.current);
    }
  };

  const raw = local;
  const valid = HEX_RE.test(raw);

  return (
    <div className="flex flex-col gap-1">
      <span className="text-sm font-medium">{label}</span>
      <div className="flex items-center gap-2">
        <input
          type="color"
          value={valid ? raw.slice(0, 7) : '#000000'}
          onChange={(e) => scheduleCommit(e.target.value)}
          onInput={(e) => scheduleCommit((e.target as HTMLInputElement).value)}
          onBlur={commitNow}
          className="h-10 w-14 shrink-0 cursor-pointer rounded-card border border-surface-border p-0.5"
          aria-label={`${label} — paleta`}
        />
        <Input
          value={raw}
          aria-invalid={!valid}
          onChange={(e) => scheduleCommit(e.target.value)}
          onBlur={commitNow}
          className="flex-1"
          placeholder="#RRGGBB"
        />
      </div>
      {!valid && <span className="text-xs text-danger">Use #RRGGBB.</span>}
    </div>
  );
}

/**
 * `onChange` é ignorado na comparação de propriedades de propósito: o `ColorGrid`
 * recria essa função a cada render, mas ela sempre encaminha para o mesmo
 * `set` do `useThemeEditor`. Comparar só `label`/`value` deixa o `memo` efetivo.
 */
export const ColorField = memo(
  ColorFieldImpl,
  (a, b) =>
    a.label === b.label && a.value === b.value && a.commitDelayMs === b.commitDelayMs,
);
