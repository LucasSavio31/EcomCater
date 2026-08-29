import { resolveMediaUrl } from '@/lib/media';
import type { FooterSeals } from '@/modules/theme';

/**
 * Selos do rodapé: Formas de Pagamento / Formas de Entrega / Loja Segura.
 * Se a coluna tem imagens enviadas no admin (menu "Selos do rodapé"), mostra
 * elas; senão cai nos badges de texto/URL.
 */
export function FooterSealsBar({ seals }: { seals: FooterSeals }) {
  const norm = (c: Partial<FooterSeals['payment']> | undefined) => ({
    title: c?.title ?? '',
    text: c?.text ?? '',
    badges: c?.badges ?? [],
    image_urls: c?.image_urls ?? [],
  });
  const columns = [
    { key: 'payment', ...norm(seals?.payment) },
    { key: 'shipping', ...norm(seals?.shipping) },
    { key: 'security', ...norm(seals?.security) },
  ].filter((c) => c.image_urls.length > 0 || c.badges.length > 0 || c.text);

  if (columns.length === 0) return null;

  return (
    <div className="grid gap-6 border-t border-footer-fg/15 pt-6 sm:grid-cols-3">
      {columns.map((col) => (
        <div key={col.key} className="flex flex-col gap-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-footer-fg/80">
            {col.title}
          </p>

          {col.image_urls.length > 0 ? (
            <ul className="flex flex-wrap items-center gap-2">
              {col.image_urls.map((url, i) => {
                const src = resolveMediaUrl(url);
                if (!src) return null;
                return (
                  <li key={i}>
                    {/* eslint-disable-next-line @next/next/no-img-element -- selo enviado no admin */}
                    <img src={src} alt="" loading="lazy" className="h-8 w-auto rounded bg-white object-contain px-1" />
                  </li>
                );
              })}
            </ul>
          ) : (
            col.badges.length > 0 && (
              <ul className="flex flex-wrap items-center gap-1.5">
                {col.badges.map((badge) => (
                  <li key={badge}>
                    <Badge value={badge} />
                  </li>
                ))}
              </ul>
            )
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
