'use client';

import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { cn } from '../lib/cn';
import { useFocusTrap } from '../lib/use-focus-trap';

export type DrawerSide = 'left' | 'right';

export interface DrawerProps {
  open: boolean;
  onClose: () => void;
  side?: DrawerSide;
  title?: ReactNode;
  children: ReactNode;
  /** id opcional para o elemento de título (ligado via aria-labelledby). */
  labelledById?: string;
  className?: string;
}

const SIDE: Record<DrawerSide, string> = {
  left: 'left-0 border-r',
  right: 'right-0 border-l',
};

/** Painel lateral modal com foco preso e fechamento por Esc / clique no backdrop. */
export function Drawer({
  open,
  onClose,
  side = 'right',
  title,
  children,
  labelledById,
  className,
}: DrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  useFocusTrap(panelRef, { active: open, onEscape: onClose });

  useEffect(() => {
    if (!open) return;
    const { overflow } = document.body.style;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = overflow;
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50" role="presentation">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === 'string' ? title : undefined}
        aria-labelledby={labelledById}
        tabIndex={-1}
        className={cn(
          'absolute top-0 flex h-full w-[min(100vw,22rem)] flex-col bg-surface text-text shadow-xl',
          'border-surface-border focus:outline-none',
          SIDE[side],
          className,
        )}
      >
        {title && (
          <div className="flex items-center justify-between border-b border-surface-border p-4">
            <h2 id={labelledById} className="text-base font-semibold">
              {title}
            </h2>
            <button
              type="button"
              onClick={onClose}
              aria-label="Fechar"
              className="min-h-touch min-w-touch rounded-card px-2 hover:bg-bg-subtle"
            >
              <span aria-hidden="true">×</span>
            </button>
          </div>
        )}
        <div className="flex-1 overflow-y-auto p-4">{children}</div>
      </div>
    </div>
  );
}
