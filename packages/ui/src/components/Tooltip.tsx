import type { ReactNode } from 'react';
import { cn } from '../lib/cn';

export type TooltipSide = 'top' | 'bottom' | 'left' | 'right';

export interface TooltipProps {
  /** Texto do balão. */
  label: string;
  children: ReactNode;
  side?: TooltipSide;
  className?: string;
}

const SIDE_CLASSES: Record<TooltipSide, string> = {
  top: 'bottom-full left-1/2 mb-1.5 -translate-x-1/2',
  bottom: 'top-full left-1/2 mt-1.5 -translate-x-1/2',
  left: 'right-full top-1/2 mr-1.5 -translate-y-1/2',
  right: 'left-full top-1/2 ml-1.5 -translate-y-1/2',
};

/**
 * Tooltip por CSS puro — pensado pra botões só-de-ícone (sem texto visível),
 * onde o `title` nativo do navegador é a única pista do que o botão faz (lento
 * pra aparecer, sem estilo, cortado às vezes). Aparece no hover E no foco por
 * teclado, então continua acessível sem mouse.
 *
 * Não substitui `aria-label`/`title` no elemento filho — o balão é decorativo
 * (`aria-hidden`); quem lê tela usa o próprio `aria-label` do botão.
 */
export function Tooltip({ label, children, side = 'top', className }: TooltipProps) {
  return (
    <span className={cn('group/tooltip relative inline-flex', className)}>
      {children}
      <span
        aria-hidden="true"
        className={cn(
          'pointer-events-none absolute z-20 whitespace-nowrap rounded-card bg-text px-2 py-1',
          'text-xs font-medium text-bg opacity-0 shadow-lg transition-opacity duration-100',
          'group-hover/tooltip:opacity-100 group-focus-within/tooltip:opacity-100',
          SIDE_CLASSES[side],
        )}
      >
        {label}
      </span>
    </span>
  );
}
