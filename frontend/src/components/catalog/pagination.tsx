import Link from 'next/link';

interface PaginationProps {
  page: number;
  pages: number;
  /** Base já com querystring existente, sem `page`. Ex.: `/categoria/x?sort=…`. */
  hrefForPage: (page: number) => string;
}

/** Paginação numérica acessível (rel prev/next para SEO). */
export function Pagination({ page, pages, hrefForPage }: PaginationProps) {
  if (pages <= 1) return null;

  const windowSize = 2;
  const nums: number[] = [];
  for (let p = 1; p <= pages; p += 1) {
    if (p === 1 || p === pages || (p >= page - windowSize && p <= page + windowSize)) {
      nums.push(p);
    }
  }

  return (
    <nav aria-label="Paginação" className="flex items-center justify-center gap-1">
      <PageLink disabled={page <= 1} href={hrefForPage(page - 1)} rel="prev">
        Anterior
      </PageLink>
      <ul className="flex items-center gap-1">
        {nums.map((num, i) => {
          const prev = nums[i - 1];
          const gap = typeof prev === 'number' && num - prev > 1;
          return (
            <li key={num} className="flex items-center gap-1">
              {gap && <span className="px-1 text-text-muted">…</span>}
              <Link
                href={hrefForPage(num)}
                aria-current={num === page ? 'page' : undefined}
                className={`inline-flex min-h-touch min-w-touch items-center justify-center rounded-card px-3 text-sm ${
                  num === page
                    ? 'bg-primary text-primary-fg'
                    : 'border border-surface-border hover:bg-bg-subtle'
                }`}
              >
                {num}
              </Link>
            </li>
          );
        })}
      </ul>
      <PageLink disabled={page >= pages} href={hrefForPage(page + 1)} rel="next">
        Próxima
      </PageLink>
    </nav>
  );
}

function PageLink({
  href,
  disabled,
  rel,
  children,
}: {
  href: string;
  disabled: boolean;
  rel: 'prev' | 'next';
  children: React.ReactNode;
}) {
  if (disabled) {
    return (
      <span className="inline-flex min-h-touch items-center rounded-card px-3 text-sm text-text-muted opacity-50">
        {children}
      </span>
    );
  }
  return (
    <Link
      href={href}
      rel={rel}
      className="inline-flex min-h-touch items-center rounded-card border border-surface-border px-3 text-sm hover:bg-bg-subtle"
    >
      {children}
    </Link>
  );
}
