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

  // coluna que ocupa a altura da tela: o <main> cresce (flex-1) e empurra o
  // rodapé pra base mesmo quando o conteúdo é curto (sticky footer).
  return (
    <div className="flex min-h-dvh flex-col">
      {header}
      <main id="conteudo" className="mx-auto w-full max-w-header flex-1 px-4 py-6 sm:py-8">
        {children}
      </main>
      {footer}
    </div>
  );
}
