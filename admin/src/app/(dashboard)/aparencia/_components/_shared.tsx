'use client';

import type { ReactNode } from 'react';
import { Button, Card } from '@ecom/ui';
import { ColorField } from '@/components/color-field';
import type { Theme } from '@/modules/appearance/api';

export type ColorFieldDef = { key: keyof Theme; label: string };

export function ColorGrid({
  fields,
  theme,
  set,
  cols = 2,
}: {
  fields: ColorFieldDef[];
  theme: Theme;
  set: <K extends keyof Theme>(k: K, v: Theme[K]) => void;
  cols?: 2 | 3;
}) {
  return (
    <div className={`grid gap-4 ${cols === 3 ? 'sm:grid-cols-3' : 'sm:grid-cols-2'}`}>
      {fields.map((f) => (
        <ColorField
          key={String(f.key)}
          label={f.label}
          value={String(theme[f.key] ?? '#000000')}
          onChange={(hex) => set(f.key, hex as Theme[typeof f.key])}
        />
      ))}
    </div>
  );
}

export function SectionCard({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <Card variant="outline" className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 className="text-lg font-semibold">{title}</h2>
        {hint && <p className="text-xs text-text-muted">{hint}</p>}
      </div>
      {children}
    </Card>
  );
}

export function SaveBar({
  dirty,
  saving,
  onSave,
  onDiscard,
}: {
  dirty: boolean;
  saving: boolean;
  onSave: () => void;
  onDiscard: () => void;
}) {
  return (
    <div className="mt-2 flex items-center gap-3 border-t border-surface-border pt-4">
      <Button loading={saving} disabled={!dirty} onClick={onSave}>
        Salvar
      </Button>
      {dirty && (
        <button type="button" className="text-sm text-text-muted underline" onClick={onDiscard}>
          Descartar alterações
        </button>
      )}
      {dirty && (
        <span className="text-xs text-text-muted">Alterações não salvas.</span>
      )}
    </div>
  );
}
