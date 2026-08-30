'use client';

import { useEffect, useRef, useState } from 'react';
import { cn } from '@ecom/ui';

interface RichTextareaProps {
  label?: string;
  value: string;
  onChange: (value: string) => void;
  rows?: number;
  hint?: string;
}

const FONTS: Array<{ label: string; value: string }> = [
  { label: 'Fonte padrão', value: '' },
  { label: 'Arial', value: 'Arial, Helvetica, sans-serif' },
  { label: 'Georgia', value: 'Georgia, serif' },
  { label: 'Times', value: '"Times New Roman", Times, serif' },
  { label: 'Courier', value: '"Courier New", Courier, monospace' },
  { label: 'Verdana', value: 'Verdana, Geneva, sans-serif' },
];

const SIZES: Array<{ label: string; value: string }> = [
  { label: 'Tamanho', value: '' },
  { label: 'Pequeno', value: '13px' },
  { label: 'Normal', value: '16px' },
  { label: 'Médio', value: '20px' },
  { label: 'Grande', value: '26px' },
  { label: 'Enorme', value: '34px' },
];

/**
 * Editor de texto visual (WYSIWYG). O que se digita já aparece formatado —
 * negrito, itálico, sublinhado, títulos, listas, link, fonte e tamanho.
 * Guarda HTML por baixo, mas o usuário nunca vê tag. Há um botão "HTML" para
 * quem quiser editar o código na mão.
 */
export function RichTextarea({ label, value, onChange, rows = 12, hint }: RichTextareaProps) {
  const ref = useRef<HTMLDivElement>(null);
  const lastEmitted = useRef<string>(value);
  const [showHtml, setShowHtml] = useState(false);

  // monta o conteúdo inicial uma vez
  useEffect(() => {
    if (ref.current) ref.current.innerHTML = value || '';
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // sincroniza quando o valor muda por fora (ex.: trocar de página na lista)
  useEffect(() => {
    if (ref.current && value !== lastEmitted.current && document.activeElement !== ref.current) {
      ref.current.innerHTML = value || '';
      lastEmitted.current = value;
    }
  }, [value]);

  function emit(): void {
    const html = ref.current?.innerHTML ?? '';
    lastEmitted.current = html;
    onChange(html);
  }

  function exec(command: string, arg?: string): void {
    ref.current?.focus();
    try {
      document.execCommand('styleWithCSS', false, 'true');
    } catch {
      /* navegador antigo */
    }
    document.execCommand(command, false, arg);
    emit();
  }

  /** Envolve a seleção num <span> com o estilo pedido (fonte ou tamanho). */
  function applyStyle(prop: 'fontFamily' | 'fontSize', cssValue: string): void {
    const el = ref.current;
    if (!el) return;
    el.focus();
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0 || sel.isCollapsed) return;
    const range = sel.getRangeAt(0);
    if (!el.contains(range.commonAncestorContainer)) return;
    const span = document.createElement('span');
    span.style[prop] = cssValue;
    try {
      span.appendChild(range.extractContents());
      range.insertNode(span);
      // reposiciona a seleção sobre o trecho formatado
      sel.removeAllRanges();
      const after = document.createRange();
      after.selectNodeContents(span);
      sel.addRange(after);
    } catch {
      /* seleção complexa: ignora em vez de quebrar */
    }
    emit();
  }

  function addLink(): void {
    const url = window.prompt('Endereço do link (https://…)');
    if (url) exec('createLink', url);
  }

  const minHeight = `${Math.max(6, rows) * 1.6}rem`;

  return (
    <div className="flex flex-col gap-1">
      {label && <span className="text-sm font-medium text-text">{label}</span>}

      <div className="flex flex-wrap items-center gap-1 rounded-t-card border border-b-0 border-surface-border bg-bg-subtle p-1">
        <ToolbarButton onClick={() => exec('bold')} title="Negrito">
          <b>N</b>
        </ToolbarButton>
        <ToolbarButton onClick={() => exec('italic')} title="Itálico">
          <i>I</i>
        </ToolbarButton>
        <ToolbarButton onClick={() => exec('underline')} title="Sublinhado">
          <u>S</u>
        </ToolbarButton>
        <span className="mx-1 h-5 w-px bg-surface-border" />
        <ToolbarButton onClick={() => exec('formatBlock', 'H2')} title="Título">
          Título
        </ToolbarButton>
        <ToolbarButton onClick={() => exec('formatBlock', 'H3')} title="Subtítulo">
          Subtítulo
        </ToolbarButton>
        <ToolbarButton onClick={() => exec('formatBlock', 'P')} title="Parágrafo">
          ¶
        </ToolbarButton>
        <span className="mx-1 h-5 w-px bg-surface-border" />
        <ToolbarButton onClick={() => exec('insertUnorderedList')} title="Lista">
          • Lista
        </ToolbarButton>
        <ToolbarButton onClick={() => exec('insertOrderedList')} title="Lista numerada">
          1. Lista
        </ToolbarButton>
        <ToolbarButton onClick={addLink} title="Link">
          Link
        </ToolbarButton>
        <span className="mx-1 h-5 w-px bg-surface-border" />
        <select
          aria-label="Fonte"
          defaultValue=""
          onChange={(e) => {
            if (e.target.value) applyStyle('fontFamily', e.target.value);
            e.currentTarget.selectedIndex = 0;
          }}
          className="min-h-touch rounded-card border border-surface-border bg-surface px-1 text-xs text-text"
        >
          {FONTS.map((f) => (
            <option key={f.label} value={f.value}>
              {f.label}
            </option>
          ))}
        </select>
        <select
          aria-label="Tamanho"
          defaultValue=""
          onChange={(e) => {
            if (e.target.value) applyStyle('fontSize', e.target.value);
            e.currentTarget.selectedIndex = 0;
          }}
          className="min-h-touch rounded-card border border-surface-border bg-surface px-1 text-xs text-text"
        >
          {SIZES.map((s) => (
            <option key={s.label} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
        <span className="mx-1 h-5 w-px bg-surface-border" />
        <ToolbarButton
          onClick={() => setShowHtml((v) => !v)}
          title="Editar HTML"
          active={showHtml}
        >
          HTML
        </ToolbarButton>
      </div>

      {showHtml ? (
        <textarea
          value={value}
          rows={rows}
          onChange={(e) => {
            lastEmitted.current = e.target.value;
            onChange(e.target.value);
          }}
          className={cn(
            'w-full rounded-b-card border border-surface-border bg-surface px-3 py-2 font-mono text-sm text-text',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent',
          )}
        />
      ) : (
        <div
          ref={ref}
          contentEditable
          suppressContentEditableWarning
          onInput={emit}
          onBlur={emit}
          role="textbox"
          aria-multiline="true"
          aria-label={label}
          style={{ minHeight }}
          className={cn(
            'w-full overflow-y-auto rounded-b-card border border-surface-border bg-surface px-3 py-2 text-sm text-text',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent',
            '[&_h2]:mb-2 [&_h2]:mt-3 [&_h2]:text-xl [&_h2]:font-bold',
            '[&_h3]:mb-1.5 [&_h3]:mt-2.5 [&_h3]:text-lg [&_h3]:font-semibold',
            '[&_p]:my-2 [&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-6 [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-6',
            '[&_a]:text-accent [&_a]:underline',
          )}
        />
      )}

      {hint && <p className="text-xs text-text-muted">{hint}</p>}
    </div>
  );
}

function ToolbarButton({
  onClick,
  title,
  active,
  children,
}: {
  onClick: () => void;
  title: string;
  active?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={title}
      onMouseDown={(e) => e.preventDefault()} // não perde a seleção do editor
      onClick={onClick}
      className={cn(
        'min-h-touch rounded-card px-2 text-xs font-medium text-text hover:bg-surface',
        active && 'bg-surface ring-1 ring-accent',
      )}
    >
      {children}
    </button>
  );
}
