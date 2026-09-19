/** Máscaras de campos estruturados brasileiros (CPF, CNPJ, CEP, códigos
 * fiscais numéricos como CFOP/NCM/CEST) — uso em qualquer formulário que
 * peça esses dados, principalmente NF-e/fiscal, onde o formato errado é
 * rejeitado pela SEFAZ. Sempre digite-e-formate (estado guarda o valor já
 * mascarado); o back-end tira a pontuação de novo antes de montar o XML.
 */

export function onlyDigits(value: string): string {
  return value.replace(/\D/g, '');
}

/** Progressiva 000.000.000-00 */
export function maskCpf(value: string): string {
  const d = onlyDigits(value).slice(0, 11);
  let out = d.slice(0, 3);
  if (d.length > 3) out += `.${d.slice(3, 6)}`;
  if (d.length > 6) out += `.${d.slice(6, 9)}`;
  if (d.length > 9) out += `-${d.slice(9, 11)}`;
  return out;
}

/** Progressiva 00.000.000/0000-00 */
export function maskCnpj(value: string): string {
  const d = onlyDigits(value).slice(0, 14);
  let out = d.slice(0, 2);
  if (d.length > 2) out += `.${d.slice(2, 5)}`;
  if (d.length > 5) out += `.${d.slice(5, 8)}`;
  if (d.length > 8) out += `/${d.slice(8, 12)}`;
  if (d.length > 12) out += `-${d.slice(12, 14)}`;
  return out;
}

/** CPF (11 dígitos) ou CNPJ (14), decide sozinho pelo tamanho digitado. */
export function maskCpfCnpj(value: string): string {
  const d = onlyDigits(value);
  return d.length > 11 ? maskCnpj(value) : maskCpf(value);
}

/** Progressiva 00000-000 */
export function maskCep(value: string): string {
  const d = onlyDigits(value).slice(0, 8);
  return d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d;
}

/** Só dígitos, com teto de tamanho — pra CFOP (4), NCM (8), CEST (7) etc. */
export function maskDigits(value: string, maxLen: number): string {
  return onlyDigits(value).slice(0, maxLen);
}

export function formatCpf(cpf: string | null | undefined): string {
  if (!cpf) return '—';
  const d = onlyDigits(cpf);
  if (d.length !== 11) return cpf;
  return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`;
}

export function formatCnpj(cnpj: string | null | undefined): string {
  if (!cnpj) return '—';
  const d = onlyDigits(cnpj);
  if (d.length !== 14) return cnpj;
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`;
}
