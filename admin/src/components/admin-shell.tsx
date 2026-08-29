'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Button, Drawer, cn } from '@ecom/ui';
import { useAdminAuth } from '@/modules/auth';

interface NavItem {
  href: string;
  label: string;
}

const NAV: NavItem[] = [
  { href: '/', label: 'Dashboard' },
  { href: '/produtos', label: 'Produtos' },
  { href: '/categorias', label: 'Categorias' },
  { href: '/pedidos', label: 'Pedidos' },
  { href: '/clientes', label: 'Clientes' },
  { href: '/promocoes', label: 'Promoções' },
  { href: '/menus', label: 'Menus' },
  { href: '/aparencia', label: 'Aparência' },
  { href: '/modulos', label: 'Módulos' },
  { href: '/smtp', label: 'SMTP' },
  { href: '/usuarios', label: 'Usuários' },
];

function isActive(pathname: string, href: string): boolean {
  if (href === '/') return pathname === '/';
  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Navegação do painel" className="flex flex-col gap-1">
      {NAV.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          onClick={onNavigate}
          aria-current={isActive(pathname, item.href) ? 'page' : undefined}
          className={cn(
            'flex min-h-touch items-center rounded-card px-3 text-sm font-medium transition',
            isActive(pathname, item.href)
              ? 'bg-primary text-primary-fg'
              : 'text-text hover:bg-bg-subtle',
          )}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}

export function AdminShell({ children }: { children: React.ReactNode }) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { user, signOut } = useAdminAuth();

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[16rem_1fr]">
      <a href="#painel-conteudo" className="skip-link rounded-card bg-primary px-3 py-2 text-primary-fg">
        Pular para o conteúdo
      </a>

      {/* Sidebar desktop */}
      <aside className="hidden border-r border-surface-border bg-surface p-4 lg:block">
        <div className="mb-6 px-3 text-lg font-semibold">Painel</div>
        <NavLinks />
      </aside>

      {/* Sidebar mobile (drawer) */}
      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} side="left" title="Painel">
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
