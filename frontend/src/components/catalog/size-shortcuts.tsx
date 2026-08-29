import Link from 'next/link';

export interface SizeShortcut {
  label: string;
  url: string;
}

interface SizeShortcutsProps {
  shortcuts: SizeShortcut[];
  heading?: string;
}

/** Bloco "Compre por tamanho/numeração" — botões quadrados grandes (toque ≥44px). */
export function SizeShortcuts({ shortcuts, heading = 'Compre por numeração' }: SizeShortcutsProps) {
  if (shortcuts.length === 0) return null;
  return (
    <section aria-labelledby="size-shortcuts-title" className="flex flex-col gap-3">
      <h2 id="size-shortcuts-title" className="text-lg font-semibold">
        {heading}
      </h2>
      <ul className="flex flex-wrap gap-2">
        {shortcuts.map((shortcut) => (
          <li key={`${shortcut.label}-${shortcut.url}`}>
            <Link
              href={shortcut.url}
              className="inline-flex min-h-touch min-w-touch items-center justify-center rounded-card border border-surface-border bg-surface px-4 text-sm font-medium hover:border-primary hover:bg-bg-subtle"
            >
              {shortcut.label}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
