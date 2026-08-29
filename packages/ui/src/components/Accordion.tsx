'use client';

import { useId, useState } from 'react';
import type { ReactNode } from 'react';
import { cn } from '../lib/cn';

export interface AccordionItem {
  id: string;
  title: ReactNode;
  content: ReactNode;
}

export interface AccordionProps {
  items: AccordionItem[];
  /** Permite mais de um painel aberto ao mesmo tempo. */
  multiple?: boolean;
  /** ids abertos inicialmente. */
  defaultOpen?: string[];
  className?: string;
}

/** Lista de painéis expansíveis com padrão ARIA (button + region). */
export function Accordion({ items, multiple = false, defaultOpen = [], className }: AccordionProps) {
  const [open, setOpen] = useState<Set<string>>(() => new Set(defaultOpen));
  const baseId = useId();

  const toggle = (id: string): void => {
    setOpen((prev) => {
      const next = new Set(multiple ? prev : []);
      if (prev.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className={cn('divide-y divide-surface-border rounded-card border border-surface-border', className)}>
      {items.map((item) => {
        const isOpen = open.has(item.id);
        const btnId = `${baseId}-${item.id}-btn`;
        const panelId = `${baseId}-${item.id}-panel`;
        return (
          <div key={item.id}>
            <h3 className="m-0">
              <button
                type="button"
                id={btnId}
                aria-expanded={isOpen}
                aria-controls={panelId}
                onClick={() => toggle(item.id)}
                className="flex min-h-touch w-full items-center justify-between gap-4 px-4 py-3 text-left text-sm font-medium text-text hover:bg-bg-subtle focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              >
                {item.title}
                <span aria-hidden="true" className="text-text-muted">
                  {isOpen ? '–' : '+'}
                </span>
              </button>
            </h3>
            <div
              id={panelId}
              role="region"
              aria-labelledby={btnId}
              hidden={!isOpen}
              className="px-4 pb-4 text-sm text-text-muted"
            >
              {item.content}
            </div>
          </div>
        );
      })}
    </div>
  );
}
