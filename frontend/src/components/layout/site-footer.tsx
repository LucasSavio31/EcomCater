import Link from 'next/link';
import Image from 'next/image';
import type { ThemeSettings } from '@/modules/theme';
import type { Menu } from '@/modules/menus/types';
import { resolveMediaUrl } from '@/lib/media';
import { WhatsappIcon } from '@/components/icons';
import { NewsletterForm } from './newsletter-form';
import { PaymentFlags } from './payment-flags';
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

  const waDigits = theme.whatsapp_number?.replace(/\D/g, '') ?? '';
  const year = new Date().getFullYear();

  return (
    <footer className="mt-16 border-t border-surface-border bg-footer text-footer-fg">
      <div className="mx-auto max-w-header px-4 py-10">
        {/* Newsletter */}
        <div className="mb-8 rounded-card border border-surface-border bg-surface p-5 text-text">
          <h2 className="text-base font-semibold">Receba novidades e ofertas</h2>
          <p className="mb-3 text-sm text-text-muted">
            Cadastre seu e-mail e fique por dentro dos lançamentos.
          </p>
          <NewsletterForm />
        </div>

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
            {waDigits && (
              <a
                href={`https://wa.me/${waDigits}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-sm text-footer-fg/70 hover:text-footer-fg"
              >
                <WhatsappIcon className="h-5 w-5" />
                {theme.whatsapp_number}
              </a>
            )}
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

        {/* Pagamento */}
        <div className="mt-8 flex flex-col gap-3 border-t border-footer-fg/15 pt-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-footer-fg/70">
              Formas de pagamento
            </p>
            <PaymentFlags />
          </div>
        </div>

        {/* Legal */}
        <div className="mt-6 border-t border-footer-fg/15 pt-6 text-xs text-footer-fg/70">
          <p>
            {storeName} — CNPJ 00.000.000/0001-00. Endereço comercial disponível na página{' '}
            <Link href="/pagina/fale-conosco" className="underline hover:text-footer-fg">
              Fale conosco
            </Link>
            .
          </p>
          <p className="mt-1">
            © {year} {storeName}. Todos os direitos reservados. Preços e condições de pagamento
            exclusivos para compras via internet.
          </p>
        </div>
      </div>
    </footer>
  );
}
