import type { Metadata, Viewport } from 'next';
import './globals.css';
import { getTheme, ThemeStyle } from '@/modules/theme';
import { ServiceWorker } from '@/components/service-worker';
import { SITE_NAME, SITE_URL } from '@/lib/seo';

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: SITE_NAME, template: `%s · ${SITE_NAME}` },
  description: 'Loja online.',
  manifest: '/manifest.json',
  applicationName: SITE_NAME,
  icons: {
    icon: '/icons/icon-192.png',
    apple: '/icons/icon-192.png',
  },
};

export const viewport: Viewport = {
  themeColor: '#111111',
  width: 'device-width',
  initialScale: 1,
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const theme = await getTheme();

  return (
    <html lang="pt-BR">
      <body className="min-h-dvh bg-bg text-text">
        {/* CSS vars do tema — primeiro nó do body, aplicado antes do paint (sem FOUC). */}
        <ThemeStyle theme={theme} />

        <a href="#conteudo" className="skip-link rounded-card bg-primary px-3 py-2 text-primary-fg">
          Pular para o conteúdo
        </a>

        {/* Header MÍNIMO — conteúdo real (mega menu, busca, mini-cart) vem na Fase 3. */}
        <header className="border-b border-surface-border">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
            <span className="text-lg font-semibold">{SITE_NAME}</span>
            <nav aria-label="Ações" className="text-sm text-text-muted">
              <span>Placeholder de header</span>
            </nav>
          </div>
        </header>

        <main id="conteudo" className="mx-auto max-w-6xl px-4 py-8">
          {children}
        </main>

        {/* Footer MÍNIMO — links institucionais, newsletter e bandeiras vêm na Fase 3. */}
        <footer className="mt-16 border-t border-surface-border">
          <div className="mx-auto max-w-6xl px-4 py-8 text-sm text-text-muted">
            <p>
              © {new Date().getFullYear()} {SITE_NAME}. Placeholder de footer.
            </p>
          </div>
        </footer>

        <ServiceWorker />
      </body>
    </html>
  );
}
