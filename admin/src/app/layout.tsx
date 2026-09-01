import type { Metadata, Viewport } from 'next';
import './globals.css';
import { getAdminTheme, themeToCssVars } from '@/modules/theme/theme';

export const metadata: Metadata = {
  title: { default: 'Painel', template: '%s · Painel' },
  description: 'Painel administrativo da loja.',
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  themeColor: '#111111',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default async function AdminRootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const theme = await getAdminTheme();

  return (
    <html lang="pt-BR">
      <body className="min-h-dvh bg-bg-subtle text-text">
        {/* Mesmo tema da loja — CSS vars inline no SSR (sem FOUC). */}
        <style id="ecom-theme" dangerouslySetInnerHTML={{ __html: themeToCssVars(theme) }} />
        {children}
      </body>
    </html>
  );
}
