import type { HTMLAttributes } from 'react';
import { cn } from '../lib/cn';

export interface SpinnerProps extends HTMLAttributes<HTMLSpanElement> {
  size?: 'sm' | 'md' | 'lg';
  /** Rótulo acessível anunciado por leitores de tela. */
  label?: string;
}

const SIZES = {
  sm: 'h-4 w-4 border-2',
  md: 'h-6 w-6 border-2',
  lg: 'h-8 w-8 border-[3px]',
} as const;

export function Spinner({ size = 'md', label = 'Carregando…', className, ...rest }: SpinnerProps) {
  return (
    <span role="status" aria-live="polite" className={cn('inline-flex', className)} {...rest}>
      <span
        aria-hidden="true"
        className={cn(
          'animate-spin rounded-full border-current border-r-transparent',
          SIZES[size],
        )}
      />
      <span className="sr-only">{label}</span>
    </span>
  );
}
