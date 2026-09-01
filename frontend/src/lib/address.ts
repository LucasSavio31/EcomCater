/**
 * Número da residência: **só dígitos** ou exatamente **"S/N"** (sem número).
 *
 * Qualquer letra (s/n em qualquer forma: "s", "sn", "sem numero"…) colapsa para
 * "S/N" — garante um único S, uma única "/" e um único N. Sem letra, só dígitos.
 * O campo usa `inputMode="numeric"` para abrir o teclado numérico no celular.
 */
export function maskHouseNumber(v: string): string {
  if (/[a-z]/i.test(v)) return 'S/N';
  return v.replace(/\D/g, '').slice(0, 10);
}
