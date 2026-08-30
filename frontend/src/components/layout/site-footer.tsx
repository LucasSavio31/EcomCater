import Link from 'next/link';
import Image from 'next/image';
import type { ThemeSettings } from '@/modules/theme';
import type { Menu } from '@/modules/menus/types';
import { resolveMediaUrl } from '@/lib/media';
import { FooterSealsBar } from './footer-seals';
import { SocialIcons, type SocialLink } from './social-icons';

interface SiteFooterProps {
  theme: ThemeSettings;
  menu: Menu | null;
  storeName: string;
  socialLinks?: SocialLink[];
}

/** Slugs institucionais padrão, usados só se o menu de rodapé vier vazio. */
const FALLBACK_LINKS: { label: string; url: string }[] = [
  { label: 'Quem somos', url: '/pagina/quem-somos' },
  { label: 'Como comprar', url: '/pagina/como-comprar' },
  { label: 'Entregas', url: '/pagina/entregas' },
  { label: 'Trocas e devoluções', url: '/pagina/trocas-e-devolucoes' },
  { label: 'Política de privacidade', url: '/pagina/politica-de-privacidade' },
  { label: 'Política de vendas', url: '/pagina/politica-de-vendas' },
  { label: 'Fale conosco', url: '/pagina/fale-conosco' },
];

export function SiteFooter({ theme, menu, storeName, socialLinks = [] }: SiteFooterProps) {
  const logo = resolveMediaUrl(theme.logo_url);
  const columns =
    menu && menu.items.length > 0
      ? menu.items
      : [{ id: 'inst', label: 'Institucional', url: '#', highlight: false, is_megamenu: false, size_shortcuts: [], children: FALLBACK_LINKS.map((l, i) => ({ id: `fb-${i}`, label: l.label, url: l.url, highlight: false, is_megamenu: false, size_shortcuts: [], children: [] })) }];

  return (
    <footer className="mt-16 border-t border-surface-border bg-footer text-footer-fg">
      <div className="mx-auto max-w-header px-4 py-10">
        <div className="grid gap-8 md:grid-cols-[1.2fr_repeat(3,1fr)]">
          {/* Marca + contato */}
          <div className="flex flex-col gap-3">
            <Link href="/" aria-label={`${storeName} — início`}>
              {logo ? (
                <span className="relative block h-9 w-[150px]">
                  <Image src={logo} alt={storeName} fill sizes="150px" className="object-contain object-left" />
                </span>
              ) : (
                <span className="text-lg font-bold">{storeName}</span>
              )}
            </Link>
            <p className="text-xs leading-relaxed text-footer-fg/60">
              {storeName} — Preços e condições de pagamento exclusivos para compras via internet.
              Endereço comercial disponível na página{' '}
              <Link href="/pagina/fale-conosco" className="underline hover:text-footer-fg">
                Fale conosco
              </Link>
              .
            </p>
            <SocialIcons links={socialLinks} />
          </div>

          {/* Colunas de links */}
          {columns.slice(0, 3).map((col) => (
            <nav key={col.id} aria-label={col.label}>
              <h2 className="mb-2 text-sm font-semibold text-footer-fg">{col.label}</h2>
              <ul className="flex flex-col gap-1.5">
                {(col.children.length > 0 ? col.children : [col]).map((link) => (
                  <li key={link.id}>
                    <Link
                      href={link.url}
                      className="text-sm text-footer-fg/70 hover:text-footer-fg hover:underline"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>

        {/* Selos: pagamento / entrega / loja segura */}
        {theme.footer_seals_enabled && (
          <div className="mt-8">
            <FooterSealsBar seals={theme.footer_seals_json} />
          </div>
        )}
      </div>
    </footer>
  );
}
