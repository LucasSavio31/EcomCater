import Image from 'next/image';
import { resolveMediaUrl } from '@/lib/media';
import { resolveCopyright } from '@/lib/copyright';
import type { ThemeSettings } from '@/modules/theme';

/** Cabeçalho mínimo do checkout: logo + selo "Compra segura". */
export function CheckoutHeader({ theme, storeName }: { theme: ThemeSettings; storeName: string }) {
  const logo = resolveMediaUrl(theme.logo_url);
  return (
    <header
      className="border-b border-surface-border text-header-fg"
      style={{ background: theme.checkout_header_bg_color }}
    >
      <div
        className="mx-auto flex items-center justify-between gap-4 px-4 py-4"
        style={{ maxWidth: `${theme.checkout_container_width_px}px` }}
      >
        {/* Logo sem link: no checkout não há saída a não ser o "voltar" do navegador. */}
        <span className="flex items-center gap-2">
          {logo ? (
            <span className="relative block h-8 w-[150px]">
              <Image src={logo} alt={storeName} fill sizes="150px" className="object-contain object-left" priority />
            </span>
          ) : (
            <span className="text-lg font-bold">{storeName}</span>
          )}
        </span>
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
 * Rodapé do checkout: por decisão de projeto, SEM os selos/menu do rodapé da
 * loja (aqui é só o fluxo de pagamento) — só o texto puro do copyright,
 * puxado dos mesmos dados/template da loja.
 */
export function CheckoutFooter({ theme, storeName }: { theme: ThemeSettings; storeName?: string }) {
  const copyright = resolveCopyright(theme, storeName);
  if (!copyright) return null;
  return (
    <footer className="mt-10 px-4 py-6 text-center text-xs text-text-muted">
      {copyright}
    </footer>
  );
}
