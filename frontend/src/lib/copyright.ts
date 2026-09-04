import type { ThemeSettings } from '@/modules/theme';

/** `12345678000199` -> `12.345.678/0001-99`. Deixa como veio se não tiver 14 dígitos. */
export function formatCnpj(raw?: string | null): string {
  const d = (raw ?? '').replace(/\D/g, '');
  if (d.length !== 14) return (raw ?? '').trim();
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`;
}

/**
 * Resolve o texto de copyright do rodapé (`theme.footer_copyright_text`),
 * substituindo `{ano}`/`{loja}`/`{cnpj}` pelos dados reais da loja. Usado no
 * rodapé da loja e no rodapé do checkout — mesma fonte, mesmo texto.
 */
export function resolveCopyright(theme: ThemeSettings, fallbackStoreName = ''): string {
  const legalName = theme.legal_name || theme.store_name || fallbackStoreName;
  const cnpj = formatCnpj(theme.cnpj);
  return (theme.footer_copyright_text || '')
    .replace(/\{ano\}/g, String(new Date().getFullYear()))
    .replace(/\{loja\}/g, legalName)
    .replace(/\{cnpj\}/g, cnpj || '—')
    // limpa "CNPJ —." quando não há CNPJ cadastrado
    .replace(/\s*[—-]?\s*CNPJ\s*—\.?/i, '.')
    .trim();
}
