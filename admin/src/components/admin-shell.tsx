'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Button, Drawer, cn } from '@ecom/ui';
import { useAdminAuth } from '@/modules/auth';

interface NavItem {
  href: string;
  label: string;
  icon: string;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

/** Navegação em grupos, no estilo do menu lateral do WooCommerce. */
const NAV_GROUPS: NavGroup[] = [
  {
    title: 'Visão geral',
    items: [{ href: '/', label: 'Painel', icon: '📊' }],
  },
  {
    title: 'Catálogo',
    items: [
      { href: '/produtos', label: 'Produtos', icon: '👟' },
      { href: '/categorias', label: 'Categorias', icon: '🗂️' },
    ],
  },
  {
    title: 'Vendas',
    items: [
      { href: '/pedidos', label: 'Pedidos', icon: '🧾' },
      { href: '/clientes', label: 'Clientes', icon: '👥' },
      { href: '/promocoes', label: 'Promoções', icon: '🏷️' },
    ],
  },
  {
    title: 'Marketing',
    items: [{ href: '/rastreamento', label: 'Rastreamento e anúncios', icon: '📈' }],
  },
  {
    title: 'Loja',
    items: [
      { href: '/aparencia', label: 'Aparência', icon: '🎨' },
      { href: '/menus', label: 'Menus', icon: '📑' },
    ],
  },
  {
    title: 'Sistema',
    items: [
      { href: '/modulos', label: 'Módulos', icon: '🧩' },
      { href: '/smtp', label: 'E-mail (SMTP)', icon: '✉️' },
      { href: '/usuarios', label: 'Usuários', icon: '🔐' },
    ],
  },
];

function isActive(pathname: string, href: string): boolean {
  if (href === '/') return pathname === '/';
  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Menu administrativo" className="flex flex-col gap-5">
      {NAV_GROUPS.map((group) => (
        <div key={group.title} className="flex flex-col gap-1">
          <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-text-muted">
            {group.title}
          </p>
          {group.items.map((item) => {
            const active = isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onNavigate}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'flex min-h-touch items-center gap-2.5 rounded-card px-3 text-sm font-medium transition',
                  active
                    ? 'bg-primary text-primary-fg'
                    : 'text-text hover:bg-bg-subtle',
                )}
              >
                <span aria-hidden className="text-base leading-none">
                  {item.icon}
                </span>
                {item.label}
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
  );
}

function SidebarHeader() {
  return (
    <div className="mb-5 border-b border-surface-border px-3 pb-4">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
        Menu administrativo
      </p>
      <p className="text-lg font-semibold">Painel da loja</p>
    </div>
  );
}

export function AdminShell({ children }: { children: React.ReactNode }) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { user, signOut } = useAdminAuth();

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[17rem_1fr]">
      <a href="#painel-conteudo" className="skip-link rounded-card bg-primary px-3 py-2 text-primary-fg">
        Pular para o conteúdo
      </a>

      {/* Sidebar desktop */}
      <aside className="hidden border-r border-surface-border bg-surface p-4 lg:block">
        <SidebarHeader />
        <NavLinks />
      </aside>

      {/* Sidebar mobile (drawer) */}
      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} side="left" title="Menu administrativo">
        <NavLinks onNavigate={() => setDrawerOpen(false)} />
      </Drawer>

      <div className="flex min-w-0 flex-col">
        <header className="flex items-center justify-between gap-4 border-b border-surface-border bg-surface px-4 py-3">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="lg:hidden"
              aria-label="Abrir menu"
              aria-expanded={drawerOpen}
              onClick={() => setDrawerOpen(true)}
            >
              ☰
            </Button>
            <span className="text-sm text-text-muted">Administração</span>
          </div>
          <div className="flex items-center gap-3">
            {user && (
              <span className="hidden text-sm text-text-muted sm:inline">
                {user.name} · {user.role}
              </span>
            )}
            <Button variant="ghost" size="sm" onClick={() => void signOut()}>
              Sair
            </Button>
          </div>
        </header>

        <main id="painel-conteudo" className="flex-1 p-4 sm:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
