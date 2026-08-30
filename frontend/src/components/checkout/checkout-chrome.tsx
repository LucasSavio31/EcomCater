import Link from 'next/link';
import Image from 'next/image';
import { resolveMediaUrl } from '@/lib/media';
import type { ThemeSettings } from '@/modules/theme';
import { FooterSealsBar } from '@/components/layout/footer-seals';

/** Cabeçalho mínimo do checkout: logo + selo "Compra segura". */
export function CheckoutHeader({ theme, storeName }: { theme: ThemeSettings; storeName: string }) {
  const logo = resolveMediaUrl(theme.logo_url);
  return (
    <header className="border-b border-surface-border bg-header text-header-fg">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-4">
        <Link href="/" aria-label={`${storeName} — início`} className="flex items-center gap-2">
          {logo ? (
            <span className="relative block h-8 w-[150px]">
              <Image src={logo} alt={storeName} fill sizes="150px" className="object-contain object-left" priority />
            </span>
          ) : (
            <span className="text-lg font-bold">{storeName}</span>
          )}
        </Link>
        <span className="inline-flex items-center gap-1.5 text-sm font-medium text-success">
          <svg aria-hidden viewBox="0 0 512 512" className="h-4 w-4 fill-current">
            <path d="M466.5 83.7l-192-80a48.15 48.15 0 0 0-36.9 0l-192 80C27.7 91.1 16 108.6 16 128c0 198.5 114.5 335.7 221.5 380.3 11.8 4.9 25.1 4.9 36.9 0C360.1 472.6 496 349.3 496 128c0-19.4-11.7-36.9-29.5-44.3zM256 446.9V64.2l175.9 73.3C426.9 288.7 340 415.7 256 446.9z" />
          </svg>
          Compra segura
        </span>
      </div>
    </header>
  );
}

/**
 * Rodapé do checkout: por decisão de projeto, aparece **somente os selos**
 * (Formas de Pagamento / Entrega / Loja Segura). Nada de menu ou copyright.
 */
export function CheckoutFooter({ theme }: { theme: ThemeSettings }) {
  if (!theme.footer_seals_enabled) return null;
  return (
    <footer className="mt-10 border-t border-surface-border bg-footer text-footer-fg">
      <div className="mx-auto max-w-5xl px-4 py-6">
        <FooterSealsBar seals={theme.footer_seals_json} />
      </div>
    </footer>
  );
}
