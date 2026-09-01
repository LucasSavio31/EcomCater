/** Helpers de formatação compartilhados pelo painel. */

export function formatBRL(cents: number | null | undefined): string {
  const value = typeof cents === 'number' ? cents : 0;
  return (value / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

/** Converte centavos para string editável em reais (ex. 1990 -> "19,90"). */
export function centsToInput(cents: number | null | undefined): string {
  if (cents == null) return '';
  return (cents / 100).toFixed(2).replace('.', ',');
}

/** Converte "19,90" / "19.90" / "1990" para centavos inteiros. Retorna null se vazio/invalido. */
export function inputToCents(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const normalized = trimmed.replace(/\s/g, '').replace(/\./g, '').replace(',', '.');
  const value = Number(normalized);
  if (!Number.isFinite(value)) return null;
  return Math.round(value * 100);
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatNumber(value: number | null | undefined): string {
  return (value ?? 0).toLocaleString('pt-BR');
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return '—';
  return `${value.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%`;
}

/**
 * Remove acentos e baixa a caixa — para comparar buscas/filtros digitados
 * com ou sem acento ("acucar" casa com "Açúcar"). Todo filtro textual do
 * painel deve passar os dois lados por aqui.
 */
export function foldAccents(text: string): string {
  return text
    .normalize('NFD')
    .split('')
    .filter((ch) => {
      const code = ch.codePointAt(0) ?? 0;
      return code < 0x0300 || code > 0x036f;
    })
    .join('')
    .toLowerCase()
    .trim();
}

/** Slug simples para pré-visualização (o backend tem a versão canônica). */
export function slugify(text: string): string {
  const stripped = text
    .normalize('NFD')
    .split('')
    .filter((ch) => {
      const code = ch.codePointAt(0) ?? 0;
      return code < 0x0300 || code > 0x036f;
    })
    .join('');
  return stripped
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '');
}
