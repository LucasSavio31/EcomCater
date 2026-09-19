'use client';

import { useCallback, useEffect, useState } from 'react';
import type { ComponentType, SVGProps } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Button, Drawer, cn } from '@ecom/ui';
import { useAdminAuth } from '@/modules/auth';
import { configApi } from '@/modules/config/api';
import { NotificationBell } from './notification-bell';

/** Nome do evento disparado (em `window`) sempre que um módulo é
 * ativado/desativado em Sistema → Módulos, pra sumir/reaparecer no menu na
 * hora, sem precisar recarregar a página. */
export const MODULES_CHANGED_EVENT = 'ecom:modules-changed';
import {
  IconAnalytics,
  IconAppearance,
  IconCategories,
  IconCheckout,
  IconCustomers,
  IconCart,
  IconDashboard,
  IconFilters,
  IconIntegrations,
  IconInvoice,
  IconLeads,
  IconMail,
  IconMenus,
  IconModules,
  IconOrders,
  IconPayment,
  IconProducts,
  IconPromotions,
  IconRuler,
  IconSeals,
  IconServer,
  IconShield,
  IconShipping,
  IconStar,
  IconUsers,
} from './nav-icons';

type Icon = ComponentType<SVGProps<SVGSVGElement>>;
interface NavItem {
  href: string;
  label: string;
  icon: Icon;
  /** Slugs de módulo (Sistema → Módulos) que dão acesso a este item — some
   * do menu quando NENHUM dos módulos listados está ativo. Vários slugs =
   * a página atende mais de um módulo (ex.: /integracoes tem WooCommerce
   * e UP Seller); some só se os dois estiverem desativados. */
  moduleSlugs?: string[];
}
interface NavGroup {
  title: string;
  items: NavItem[];
}

/** Navegação em grupos, no estilo do menu lateral do WooCommerce. */
const NAV_GROUPS: NavGroup[] = [
  {
    title: 'Visão geral',
    items: [
      { href: '/', label: 'Painel', icon: IconDashboard },
      { href: '/faturamento', label: 'Faturamento', icon: IconAnalytics },
    ],
  },
  {
    title: 'Catálogo',
    items: [
      { href: '/produtos', label: 'Produtos', icon: IconProducts },
      { href: '/categorias', label: 'Categorias', icon: IconCategories },
      { href: '/filtros', label: 'Filtros', icon: IconFilters },
      { href: '/tabelas-medidas', label: 'Tabelas de medidas', icon: IconRuler, moduleSlugs: ['size_charts'] },
      { href: '/avaliacoes', label: 'Avaliações', icon: IconStar },
    ],
  },
  {
    title: 'Vendas',
    items: [
      { href: '/pedidos', label: 'Pedidos', icon: IconOrders },
      { href: '/recuperacao-carrinho', label: 'Recuperação de carrinho', icon: IconCart, moduleSlugs: ['cart_recovery'] },
      { href: '/clientes', label: 'Clientes', icon: IconCustomers },
      { href: '/promocoes', label: 'Promoções', icon: IconPromotions, moduleSlugs: ['promotions'] },
      { href: '/pagamento', label: 'Pagamento', icon: IconPayment, moduleSlugs: ['payment'] },
      { href: '/frete', label: 'Frete', icon: IconShipping, moduleSlugs: ['shipping'] },
      { href: '/nfe', label: 'NF-e', icon: IconInvoice, moduleSlugs: ['nfe'] },
      { href: '/integracoes', label: 'Integrações', icon: IconIntegrations, moduleSlugs: ['woocommerce', 'upseller'] },
    ],
  },
  {
    title: 'Marketing',
    items: [
      { href: '/rastreamento', label: 'Rastreamento e anúncios', icon: IconAnalytics },
      { href: '/newsletter', label: 'Newsletter e popup', icon: IconMail, moduleSlugs: ['newsletter'] },
      { href: '/leads', label: 'Leads', icon: IconLeads },
    ],
  },
  {
    title: 'Loja',
    items: [
      { href: '/aparencia', label: 'Aparência', icon: IconAppearance },
      { href: '/checkout-modelo', label: 'Checkout', icon: IconCheckout },
      { href: '/selos-rodape', label: 'Selos do rodapé', icon: IconSeals },
      { href: '/menus', label: 'Menus', icon: IconMenus },
    ],
  },
  {
    title: 'Sistema',
    items: [
      { href: '/minha-conta', label: 'Minha conta', icon: IconShield },
      { href: '/infraestrutura', label: 'Infraestrutura', icon: IconServer },
      { href: '/modulos', label: 'Módulos', icon: IconModules },
      { href: '/smtp', label: 'E-mail (SMTP)', icon: IconMail },
      { href: '/usuarios', label: 'Usuários', icon: IconUsers },
    ],
  },
];

function isActive(pathname: string, href: string): boolean {
  if (href === '/') return pathname === '/';
  return pathname === href || pathname.startsWith(`${href}/`);
}

/** Slugs de módulo DESATIVADO (toggleable + enabled=false). Carrega ao
 * montar e de novo sempre que `MODULES_CHANGED_EVENT` dispara (a tela de
 * Módulos avisa assim que salva um toggle) — sem isso o menu só atualizaria
 * num F5. Começa vazio (nada escondido) pra não piscar item sumindo/
 * reaparecendo enquanto a primeira busca ainda não voltou. */
function useDisabledModuleSlugs(): Set<string> {
  const [disabled, setDisabled] = useState<Set<string>>(new Set());

  const load = useCallback(async () => {
    const res = await configApi.listModules();
    if (!res.ok) return;
    setDisabled(new Set(res.data.filter((m) => m.toggleable && !m.enabled).map((m) => m.slug)));
  }, []);

  useEffect(() => {
    void load();
    window.addEventListener(MODULES_CHANGED_EVENT, load);
    return () => window.removeEventListener(MODULES_CHANGED_EVENT, load);
  }, [load]);

  return disabled;
}

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const disabledSlugs = useDisabledModuleSlugs();
  return (
    <nav aria-label="Menu administrativo" className="flex flex-col">
      {NAV_GROUPS.map((group, gi) => {
        const items = group.items.filter(
          (item) => !item.moduleSlugs || item.moduleSlugs.some((slug) => !disabledSlugs.has(slug)),
        );
        if (items.length === 0) return null;
        return (
        <div
          key={group.title}
          className={cn(
            'flex flex-col gap-0.5 py-4',
            gi > 0 && 'border-t border-surface-border',
          )}
        >
          <p className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-text-muted">
            {group.title}
          </p>
          {items.map((item) => {
            const active = isActive(pathname, item.href);
            // só a rota EXATA (não uma sub-rota, ex.: /pedidos/2026-000001)
            // conta como "já estou aqui" — senão clicar em "Pedidos" a partir
            // do detalhe de um pedido só recarregaria o detalhe, sem voltar
            // pra lista.
            const exact = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={(e) => {
                  if (exact) {
                    e.preventDefault();
                    window.location.reload();
                    return;
                  }
                  onNavigate?.();
                }}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'flex min-h-touch items-center gap-2.5 rounded-card px-3 text-sm font-medium transition',
                  active ? 'bg-primary text-primary-fg' : 'text-text hover:bg-bg-subtle',
                )}
              >
                <Icon className="shrink-0 opacity-80" />
                {item.label}
              </Link>
            );
          })}
        </div>
        );
      })}
    </nav>
  );
}

function SidebarHeader() {
  return (
    <div className="px-3 pb-2">
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

      <aside className="hidden border-r border-surface-border bg-surface p-4 lg:block">
        <SidebarHeader />
        <NavLinks />
      </aside>

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
            <NotificationBell />
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
