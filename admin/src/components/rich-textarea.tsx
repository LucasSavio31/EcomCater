'use client';

import { useRef } from 'react';
import { cn } from '@ecom/ui';

interface RichTextareaProps {
  label?: string;
  value: string;
  onChange: (value: string) => void;
  rows?: number;
  hint?: string;
}

const ACTIONS: Array<{ label: string; before: string; after: string; block?: boolean }> = [
  { label: 'H2', before: '<h2>', after: '</h2>', block: true },
  { label: 'H3', before: '<h3>', after: '</h3>', block: true },
  { label: 'P', before: '<p>', after: '</p>', block: true },
  { label: 'B', before: '<strong>', after: '</strong>' },
  { label: 'I', before: '<em>', after: '</em>' },
  { label: 'Link', before: '<a href="https://">', after: '</a>' },
  { label: 'Lista', before: '<ul>\n  <li>', after: '</li>\n</ul>', block: true },
];

/** Textarea com uma toolbar simples que envolve a seleção em tags HTML. */
export function RichTextarea({ label, value, onChange, rows = 12, hint }: RichTextareaProps) {
  const ref = useRef<HTMLTextAreaElement>(null);

  function wrap(before: string, after: string, block?: boolean): void {
    const el = ref.current;
    if (!el) return;
    const start = el.selectionStart;
    const end = el.selectionEnd;
    const selected = value.slice(start, end);
    const insertion = `${block && start > 0 && value[start - 1] !== '\n' ? '\n' : ''}${before}${selected}${after}`;
    const next = value.slice(0, start) + insertion + value.slice(end);
    onChange(next);
    requestAnimationFrame(() => {
      el.focus();
      const cursor = start + insertion.length;
      el.setSelectionRange(cursor, cursor);
    });
  }

  return (
    <div className="flex flex-col gap-1">
      {label && <span className="text-sm font-medium text-text">{label}</span>}
      <div className="flex flex-wrap gap-1 rounded-t-card border border-b-0 border-surface-border bg-bg-subtle p-1">
        {ACTIONS.map((a) => (
          <button
            key={a.label}
            type="button"
            onClick={() => wrap(a.before, a.after, a.block)}
            className="min-h-touch rounded-card px-2 text-xs font-medium text-text hover:bg-surface"
          >
            {a.label}
          </button>
        ))}
      </div>
      <textarea
        ref={ref}
        value={value}
        rows={rows}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          'w-full rounded-b-card border border-surface-border bg-surface px-3 py-2 font-mono text-sm text-text',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent',
        )}
      />
      {hint && <p className="text-xs text-text-muted">{hint}</p>}
    </div>
  );
}
