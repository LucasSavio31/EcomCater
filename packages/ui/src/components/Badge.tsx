import type { HTMLAttributes } from 'react';
import { cn } from '../lib/cn';

export type BadgeTone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info' | 'yellow';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
}

const TONES: Record<BadgeTone, string> = {
  neutral: 'bg-bg-subtle text-text',
  accent: 'bg-accent text-accent-fg',
  success: 'bg-success text-white',
  warning: 'bg-warning text-white',
  danger: 'bg-danger text-white',
  info: 'bg-blue-600 text-white',
  // cor Tailwind padrão (não CSS var custom) -- amarelo de verdade, não o
  // âmbar de "warning" (--color-warning é laranja).
  yellow: 'bg-yellow-500 text-yellow-950',
};

export function Badge({ tone = 'neutral', className, ...rest }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-card px-2 py-0.5 text-xs font-medium',
        TONES[tone],
        className,
      )}
      {...rest}
    />
  );
}
