'use client';

import { useEffect, useId, useRef } from 'react';
import type { ReactNode } from 'react';
import { cn } from '../lib/cn';
import { useFocusTrap } from '../lib/use-focus-trap';

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const SIZES = {
  sm: 'max-w-sm',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
} as const;

/** Diálogo modal centralizado com foco preso, Esc para fechar e backdrop clicável. */
export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  size = 'md',
  className,
}: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const baseId = useId();
  const titleId = `${baseId}-title`;
  const descId = `${baseId}-desc`;
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
    <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-4" role="presentation">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} aria-hidden="true" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        aria-describedby={description ? descId : undefined}
        tabIndex={-1}
        className={cn(
          'relative z-10 flex w-full flex-col rounded-card bg-surface text-text shadow-xl focus:outline-none',
          SIZES[size],
          className,
        )}
      >
        {title && (
          <div className="flex items-start justify-between gap-4 border-b border-surface-border p-4">
            <div>
              <h2 id={titleId} className="text-base font-semibold">
                {title}
              </h2>
              {description && (
                <p id={descId} className="mt-1 text-sm text-text-muted">
                  {description}
                </p>
              )}
            </div>
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
        {children && <div className="flex-1 overflow-y-auto p-4">{children}</div>}
        {footer && (
          <div className="flex justify-end gap-2 border-t border-surface-border p-4">{footer}</div>
        )}
      </div>
    </div>
  );
}
