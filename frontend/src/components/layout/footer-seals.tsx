import type { FooterSeals } from '@/modules/theme';

/**
 * Selos do rodapé: Formas de Pagamento / Formas de Entrega / Loja Segura.
 * Cada "badge" é um nome conhecido (vira um chip estilizado) ou uma URL de
 * imagem (vira um `<img>`). Editável no admin (Aparência › Selos do rodapé).
 */
export function FooterSealsBar({ seals }: { seals: FooterSeals }) {
  const columns = [
    { key: 'payment', ...seals.payment },
    { key: 'shipping', ...seals.shipping },
    { key: 'security', ...seals.security },
  ].filter((c) => c.badges.length > 0 || c.text);

  if (columns.length === 0) return null;

  return (
    <div className="grid gap-6 border-t border-footer-fg/15 pt-6 sm:grid-cols-3">
      {columns.map((col) => (
        <div key={col.key} className="flex flex-col gap-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-footer-fg/80">
            {col.title}
          </p>
          {col.badges.length > 0 && (
            <ul className="flex flex-wrap items-center gap-1.5">
              {col.badges.map((badge) => (
                <li key={badge}>
                  <Badge value={badge} />
                </li>
              ))}
            </ul>
          )}
          {col.text && <p className="text-xs text-footer-fg/70">{col.text}</p>}
        </div>
      ))}
    </div>
  );
}

function Badge({ value }: { value: string }) {
  if (/^https?:\/\//i.test(value)) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- selo externo, sem otimização
      <img
        src={value}
        alt=""
        loading="lazy"
        className="h-6 w-auto rounded-[4px] bg-white object-contain px-1"
      />
    );
  }
  return (
    <span
      title={value}
      className="inline-flex h-6 min-w-[40px] items-center justify-center rounded-[4px] bg-white/95 px-1.5 text-[9px] font-bold uppercase tracking-wide text-gray-700"
    >
      {value}
    </span>
  );
}
