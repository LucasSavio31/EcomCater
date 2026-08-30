/** Utilidades de CPF (máscara + validação dos dígitos verificadores). */

export function onlyDigits(v: string): string {
  return v.replace(/\D/g, '');
}

/** Máscara progressiva 000.000.000-00 */
export function maskCpf(v: string): string {
  const d = onlyDigits(v).slice(0, 11);
  let out = d.slice(0, 3);
  if (d.length > 3) out += `.${d.slice(3, 6)}`;
  if (d.length > 6) out += `.${d.slice(6, 9)}`;
  if (d.length > 9) out += `-${d.slice(9, 11)}`;
  return out;
}

export function isValidCpf(v: string): boolean {
  const cpf = onlyDigits(v);
  if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) return false;
  for (const i of [9, 10]) {
    let sum = 0;
    for (let n = 0; n < i; n += 1) sum += Number(cpf[n]) * (i + 1 - n);
    let d = (sum * 10) % 11;
    if (d === 10) d = 0;
    if (d !== Number(cpf[i])) return false;
  }
  return true;
}
