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

function formatCnpj(raw?: string | null): string {
  const d = (raw ?? '').replace(/\D/g, '');
  if (d.length !== 14) return (raw ?? '').trim();
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`;
}

/** Renderiza o texto e transforma "Fale conosco" num link para a página. */
function renderNote(text: string) {
  return text.split(/(Fale conosco)/i).map((part, i) =>
    /^fale conosco$/i.test(part) ? (
      <Link key={i} href="/pagina/fale-conosco" className="underline hover:text-footer-fg">
        {part}
      </Link>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

export function SiteFooter({ theme, menu, storeName, socialLinks = [] }: SiteFooterProps) {
  const logo = resolveMediaUrl(theme.logo_url);
  const legalName = theme.legal_name || theme.store_name || storeName;
  const cnpj = formatCnpj(theme.cnpj);
  const copyright = (theme.footer_copyright_text || '')
    .replace(/\{ano\}/g, String(new Date().getFullYear()))
    .replace(/\{loja\}/g, legalName)
    .replace(/\{cnpj\}/g, cnpj || '—')
    // limpa "CNPJ —." quando não há CNPJ cadastrado
    .replace(/\s*[—-]?\s*CNPJ\s*—\.?/i, '.')
    .trim();
  const columns = (
    menu && menu.items.length > 0
      ? menu.items
      : [{ id: 'inst', label: 'Institucional', url: '#', highlight: false, is_megamenu: false, size_shortcuts: [], children: FALLBACK_LINKS.map((l, i) => ({ id: `fb-${i}`, label: l.label, url: l.url, highlight: false, is_megamenu: false, size_shortcuts: [], children: [] })) }]
  ).slice(0, 3);

  // redes sociais: só as ligadas no tema e com URL cadastrada em Dados da loja
  const social = theme.social_json ?? {};
  const socialLinksResolved: SocialLink[] = (
    [
      ['instagram', theme.footer_social_instagram_enabled],
      ['facebook', theme.footer_social_facebook_enabled],
      ['tiktok', theme.footer_social_tiktok_enabled],
      ['youtube', theme.footer_social_youtube_enabled],
    ] as const
  )
    .filter(([net, on]) => on && (social[net] ?? '').trim())
    .map(([net]) => ({ network: net, url: social[net]!.trim() }));
  if (socialLinks.length > 0) socialLinksResolved.push(...socialLinks);

  const rightCols = columns.length + (socialLinksResolved.length > 0 ? 1 : 0);

  return (
    <footer className="mt-16 border-t border-surface-border bg-footer text-footer-fg">
      <div className="mx-auto max-w-header px-4 py-10">
        <div
          className="grid gap-8"
          style={{ gridTemplateColumns: `minmax(0,1.2fr) repeat(${Math.max(rightCols, 1)}, minmax(0,1fr))` }}
        >
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
            {theme.footer_note_text?.trim() && (
              <p className="text-xs leading-relaxed text-footer-fg/70">
                {renderNote(theme.footer_note_text.trim())}
              </p>
            )}
          </div>

          {/* Colunas de links */}
          {columns.map((col) => (
            <nav key={col.id} aria-label={col.label}>
              <h2 className="mb-2 text-sm font-semibold uppercase text-footer-fg">{col.label}</h2>
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

          {/* Redes sociais */}
          {socialLinksResolved.length > 0 && (
            <div>
              <h2 className="mb-2 text-sm font-semibold uppercase text-footer-fg">Siga-nos</h2>
              <SocialIcons links={socialLinksResolved} />
            </div>
          )}
        </div>

        {/* Selos: pagamento / entrega / loja segura */}
        {theme.footer_seals_enabled && (
          <div className="mt-8">
            <FooterSealsBar seals={theme.footer_seals_json} />
          </div>
        )}
      </div>

      {/* Tarja de copyright — abaixo de tudo, cores e texto configuráveis */}
      {theme.footer_copyright_enabled && copyright && (
        <div
          style={{
            backgroundColor: theme.footer_copyright_bg_color,
            color: theme.footer_copyright_text_color,
          }}
        >
          <div className="mx-auto max-w-header px-4 py-3 text-center text-xs">{copyright}</div>
        </div>
      )}
    </footer>
  );
}
