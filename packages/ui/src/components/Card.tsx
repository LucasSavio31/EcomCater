import { forwardRef } from 'react';
import type { ElementType, HTMLAttributes } from 'react';
import { cn } from '../lib/cn';

export interface CardProps extends HTMLAttributes<HTMLElement> {
  /** `plain` sem borda/sombra; `outline` com borda; `elevated` com sombra. */
  variant?: 'plain' | 'outline' | 'elevated';
  /** Tag renderizada (default `div`). */
  as?: ElementType;
}

const VARIANTS: Record<NonNullable<CardProps['variant']>, string> = {
  plain: 'bg-surface',
  outline: 'bg-surface border border-surface-border',
  elevated: 'bg-surface shadow-sm border border-surface-border',
};

/** Superfície de conteúdo. Sempre `rounded-card` — nunca cantos retos. */
export const Card = forwardRef<HTMLElement, CardProps>(function Card(
  { variant = 'outline', as, className, ...rest },
  ref,
) {
  const Tag = (as ?? 'div') as ElementType;
  return (
    <Tag
      ref={ref}
      className={cn('rounded-card p-4 text-text', VARIANTS[variant], className)}
      {...rest}
    />
  );
});
