'use client';

import type { ReactNode } from 'react';
import { usePathname } from 'next/navigation';

/**
 * Chrome da loja. No checkout (`/checkout` e `/checkout/obrigado`) o cabeçalho e
 * o rodapé do site somem — essas páginas trazem o próprio enxoval mínimo
 * (logo + "Compra segura" + selos), no padrão de smart checkout.
 */
export function StorefrontShell({
  header,
  footer,
  children,
}: {
  header: ReactNode;
  footer: ReactNode;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const bare = pathname === '/checkout' || pathname.startsWith('/checkout/');

  if (bare) return <>{children}</>;

  return (
    <>
      {header}
      <main id="conteudo" className="mx-auto w-full max-w-header px-4 py-6 sm:py-8">
        {children}
      </main>
      {footer}
    </>
  );
}
