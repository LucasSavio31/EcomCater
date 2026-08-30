'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { Badge, Drawer } from '@ecom/ui';
import type { ThemeSettings } from '@/modules/theme';
import type { Menu, MenuItem } from '@/modules/menus/types';
import { useCart } from '@/modules/cart/cart-context';
import { resolveMediaUrl } from '@/lib/media';
import { formatBRL } from '@/lib/format';
import {
  BagIcon,
  ChevronDownIcon,
  HeadsetIcon,
  HeartIcon,
  MenuIcon,
  SearchIcon,
  UserIcon,
} from '@/components/icons';
import { SearchPanel } from './search-panel';
import { MobileNav } from './mobile-nav';

interface SiteHeaderProps {
  theme: ThemeSettings;
  menu: Menu | null;
  storeName: string;
}

function whatsappHref(raw?: string | null): string | null {
  if (!raw) return null;
  const digits = raw.replace(/\D/g, '');
  return digits ? `https://wa.me/${digits}` : null;
}

export function SiteHeader({ theme, menu, storeName }: SiteHeaderProps) {
  const pathname = usePathname();
  const { count, openMiniCart, subtotalCents, cart } = useCart();
  const [searchOpen, setSearchOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [openMega, setOpenMega] = useState<string | null>(null);

  // Fecha overlays ao trocar de rota.
  useEffect(() => {
    setSearchOpen(false);
    setMobileOpen(false);
    setOpenMega(null);
  }, [pathname]);

  const items = menu?.items ?? [];
  const logo = resolveMediaUrl(theme.logo_url);
  const wa = whatsappHref(theme.whatsapp_number);

  // Barra superior: junta o progresso do frete grátis (quando há um mínimo
  // configurado) com as mensagens do tema. Sem carrossel = só a 1ª mensagem.
  // O valor vem do carrinho (respeita cupom/desconto) e só aparece depois que
  // o cliente coloca algo no carrinho.
  const fsThreshold = cart.totals.free_shipping_threshold_cents;
  const fsRemaining = cart.totals.free_shipping_remaining_cents;
  const freeShipMsg =
    fsThreshold && subtotalCents > 0
      ? fsRemaining === 0
        ? 'Você ganhou frete grátis! 🎉'
        : `Faltam ${formatBRL(fsRemaining ?? fsThreshold)} para o frete grátis`
      : null;

  const configuredMessages = (
    theme.top_bar_enabled
      ? theme.top_bar_carousel
        ? [theme.top_bar_message, theme.top_bar_message_2, theme.top_bar_message_3]
        : [theme.top_bar_message]
      : []
  )
    .map((m) => (m ?? '').trim())
    .filter(Boolean);

  // a barra só existe se houver algo real para mostrar — nada de tarja vazia
  const topBarMessages = [freeShipMsg, ...configuredMessages].filter(Boolean) as string[];
  const rotate = topBarMessages.length > 1;
  const showTopBar = topBarMessages.length > 0;
  const [topBarIdx, setTopBarIdx] = useState(0);
  useEffect(() => {
    if (!rotate) return;
    setTopBarIdx(0);
    const id = window.setInterval(
      () => setTopBarIdx((i) => (i + 1) % topBarMessages.length),
      4000,
    );
    return () => window.clearInterval(id);
  }, [rotate, topBarMessages.length]);

  return (
    <header className="sticky top-0 z-40 border-b border-surface-border bg-header text-header-fg">
      {/* Barra utilitária (tarja superior) */}
      {showTopBar && (
        <div style={{ backgroundColor: theme.top_bar_bg_color, color: theme.top_bar_text_color }}>
          <div className="mx-auto max-w-header px-4 py-1.5 text-xs">
            <p
              key={rotate ? topBarIdx : 'static'}
              className={`truncate transition-opacity ${theme.top_bar_centered ? 'text-center' : ''}`}
            >
              {rotate ? topBarMessages[topBarIdx] : topBarMessages[0]}
            </p>
          </div>
        </div>
      )}

      {/* Barra principal */}
      <div className="mx-auto flex max-w-header items-center gap-3 px-4 py-3">
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          aria-label="Abrir menu"
          className="min-h-touch min-w-touch rounded-card p-1 lg:hidden"
        >
          <MenuIcon />
        </button>

        <Link href="/" className="flex shrink-0 items-center gap-2" aria-label={`${storeName} — início`}>
          {logo ? (
            <span className="relative block h-8 w-[140px]">
              <Image src={logo} alt={storeName} fill sizes="140px" className="object-contain object-left" priority />
            </span>
          ) : (
            <span className="text-lg font-bold">{storeName}</span>
          )}
        </Link>

        {/* Nav desktop */}
        <nav aria-label="Categorias" className="ml-4 hidden flex-1 lg:block">
          <ul className="flex items-center gap-1">
            {items.map((item) => (
              <DesktopNavItem
                key={item.id}
                item={item}
                open={openMega === item.id}
                onOpen={() => setOpenMega(item.id)}
                onClose={() => setOpenMega((cur) => (cur === item.id ? null : cur))}
              />
            ))}
          </ul>
        </nav>

        {/* Ações */}
        <div className="ml-auto flex items-center gap-0.5">
          <button
            type="button"
            onClick={() => setSearchOpen((v) => !v)}
            aria-label="Buscar"
            aria-expanded={searchOpen}
            className="min-h-touch min-w-touch rounded-card p-2 hover:bg-header-fg/10"
          >
            <SearchIcon />
          </button>
          {theme.wishlist_enabled && (
            <Link
              href="/minha-conta/favoritos"
              aria-label="Favoritos"
              className="hidden min-h-touch min-w-touch rounded-card p-2 hover:bg-header-fg/10 sm:inline-flex"
            >
              <HeartIcon />
            </Link>
          )}
          {wa ? (
            <a
              href={wa}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Atendimento por WhatsApp"
              className="hidden min-h-touch min-w-touch rounded-card p-2 hover:bg-header-fg/10 sm:inline-flex"
            >
              <HeadsetIcon />
            </a>
          ) : null}
          <Link
            href="/minha-conta"
            aria-label="Minha conta"
            className="min-h-touch min-w-touch rounded-card p-2 hover:bg-header-fg/10"
          >
            <UserIcon />
          </Link>
          {theme.mini_cart_enabled ? (
            <button
              type="button"
              onClick={openMiniCart}
              aria-label={`Carrinho${count > 0 ? ` (${count} itens)` : ''}`}
              className="relative min-h-touch min-w-touch rounded-card p-2 hover:bg-header-fg/10"
            >
              <BagIcon />
              {count > 0 && (
                <Badge
                  tone="accent"
                  className="absolute -right-0.5 -top-0.5 min-w-[1.1rem] justify-center px-1 py-0 text-[10px] leading-4"
                >
                  {count > 99 ? '99+' : count}
                </Badge>
              )}
            </button>
          ) : (
            <Link
              href="/carrinho"
              aria-label={`Carrinho${count > 0 ? ` (${count} itens)` : ''}`}
              className="relative min-h-touch min-w-touch rounded-card p-2 hover:bg-header-fg/10"
            >
              <BagIcon />
              {count > 0 && (
                <Badge
                  tone="accent"
                  className="absolute -right-0.5 -top-0.5 min-w-[1.1rem] justify-center px-1 py-0 text-[10px] leading-4"
                >
                  {count > 99 ? '99+' : count}
                </Badge>
              )}
            </Link>
          )}
        </div>
      </div>

      <SearchPanel open={searchOpen} onClose={() => setSearchOpen(false)} />

      <Drawer
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        side="left"
        title={storeName}
        labelledById="mobile-nav-title"
      >
        <MobileNav items={items} onNavigate={() => setMobileOpen(false)} whatsappHref={wa} />
      </Drawer>
    </header>
  );
}

/* ------------------------------------------------------ item de nav desktop */

interface DesktopNavItemProps {
  item: MenuItem;
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
}

function DesktopNavItem({ item, open, onOpen, onClose }: DesktopNavItemProps) {
  const hasPanel =
    item.is_megamenu && (item.children.length > 0 || item.size_shortcuts.length > 0);

  if (!hasPanel) {
    return (
      <li>
        <Link
          href={item.url}
          className={`inline-flex min-h-touch items-center rounded-card px-3 text-sm font-medium hover:bg-header-fg/10 ${
            item.highlight ? 'text-accent' : ''
          }`}
        >
          {item.label}
        </Link>
      </li>
    );
  }

  return (
    <li
      className="static"
      onMouseEnter={onOpen}
      onMouseLeave={onClose}
      onFocus={onOpen}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node)) onClose();
      }}
    >
      <Link
        href={item.url}
        aria-expanded={open}
        aria-haspopup="true"
        className={`inline-flex min-h-touch items-center gap-1 rounded-card px-3 text-sm font-medium hover:bg-header-fg/10 ${
          item.highlight ? 'text-accent' : ''
        }`}
      >
        {item.label}
        <ChevronDownIcon className="h-4 w-4" />
      </Link>

      {open && (
        <div className="absolute inset-x-0 top-full z-30 border-t border-surface-border bg-surface text-text shadow-lg">
          <div className="mx-auto grid max-w-header gap-6 px-4 py-6 md:grid-cols-[1fr_auto]">
            <div className="grid grid-cols-2 gap-x-6 gap-y-4 md:grid-cols-4">
              {item.children.map((col) => (
                <div key={col.id}>
                  <Link
                    href={col.url}
                    className="mb-1.5 block text-sm font-semibold text-text hover:underline"
                  >
                    {col.label}
                  </Link>
                  {col.children.length > 0 && (
                    <ul className="space-y-1">
                      {col.children.map((leaf) => (
                        <li key={leaf.id}>
                          <Link
                            href={leaf.url}
                            className="block text-sm text-text-muted hover:text-text hover:underline"
                          >
                            {leaf.label}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>

            {item.size_shortcuts.length > 0 && (
              <div className="min-w-[200px] rounded-card bg-bg-subtle p-4">
                <p className="mb-2 text-sm font-semibold">Compre por tamanho</p>
                <ul className="flex flex-wrap gap-2">
                  {item.size_shortcuts.map((shortcut) => (
                    <li key={`${shortcut.label}-${shortcut.url}`}>
                      <Link
                        href={shortcut.url}
                        className="inline-flex min-h-[36px] min-w-[36px] items-center justify-center rounded-card border border-surface-border bg-surface px-2 text-sm hover:border-primary"
                      >
                        {shortcut.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </li>
  );
}
