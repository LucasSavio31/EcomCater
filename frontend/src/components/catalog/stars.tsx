import { cn } from '@ecom/ui';

interface StarsProps {
  value: number;
  count?: number;
  /** Esconde o texto "(N)" ao lado. */
  hideCount?: boolean;
  className?: string;
  size?: 'sm' | 'md';
}

/** Avaliação em estrelas (0–5). Acessível: rótulo textual no `aria-label`. */
export function Stars({ value, count, hideCount, className, size = 'sm' }: StarsProps) {
  const rounded = Math.round(value * 2) / 2;
  const dim = size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4';
  const label =
    count === 0
      ? 'Nenhuma avaliação'
      : `${value.toFixed(1)} de 5${typeof count === 'number' ? ` — ${count} avaliações` : ''}`;

  if (count === 0) {
    return <span className={cn('text-xs text-text-muted', className)}>Nenhuma avaliação</span>;
  }

  return (
    <span className={cn('inline-flex items-center gap-1', className)} aria-label={label}>
      <span className="inline-flex" aria-hidden="true">
        {[0, 1, 2, 3, 4].map((i) => {
          const fill = rounded - i;
          return (
            <svg key={i} className={dim} viewBox="0 0 20 20" aria-hidden="true">
              <defs>
                <linearGradient id={`star-${i}-${Math.round(fill * 100)}`}>
                  <stop offset={`${Math.max(0, Math.min(1, fill)) * 100}%`} stopColor="currentColor" />
                  <stop offset={`${Math.max(0, Math.min(1, fill)) * 100}%`} stopColor="transparent" />
                </linearGradient>
              </defs>
              <path
                d="M10 1.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L10 15l-5.2 2.6 1-5.8L1.5 7.7l5.9-.9L10 1.5z"
                fill={fill >= 1 ? 'currentColor' : fill <= 0 ? 'transparent' : `url(#star-${i}-${Math.round(fill * 100)})`}
                stroke="currentColor"
                strokeWidth="1"
                className="text-warning"
              />
            </svg>
          );
        })}
      </span>
      {!hideCount && typeof count === 'number' && (
        <span className="text-xs text-text-muted">({count})</span>
      )}
    </span>
  );
}
