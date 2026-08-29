import Link from 'next/link';
import { ChevronRightIcon } from '@/components/icons';

export interface Crumb {
  name: string;
  url?: string;
}

/** Trilha de navegação. O último item é a página atual (sem link). */
export function Breadcrumbs({ items }: { items: Crumb[] }) {
  if (items.length === 0) return null;
  return (
    <nav aria-label="Você está em" className="text-xs text-text-muted">
      <ol className="flex flex-wrap items-center gap-1">
        {items.map((item, i) => {
          const last = i === items.length - 1;
          return (
            <li key={`${item.name}-${i}`} className="flex items-center gap-1">
              {item.url && !last ? (
                <Link href={item.url} className="hover:text-text hover:underline">
                  {item.name}
                </Link>
              ) : (
                <span aria-current={last ? 'page' : undefined} className={last ? 'text-text' : ''}>
                  {item.name}
                </span>
              )}
              {!last && <ChevronRightIcon className="h-3 w-3 text-text-muted" />}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
