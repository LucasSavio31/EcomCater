/**
 * UUID v4 com fallback.
 *
 * `crypto.randomUUID()` só existe em "secure context" (HTTPS ou localhost).
 * Ao abrir a loja pelo IP da máquina em HTTP (ex.: teste no celular na LAN),
 * o navegador não expõe `randomUUID` — aí caímos em `getRandomValues` (que
 * funciona em contexto não-seguro) e, no pior caso, em `Math.random`.
 */
export function uuid(): string {
  const c: Crypto | undefined = globalThis.crypto;

  if (c && typeof c.randomUUID === 'function') {
    return c.randomUUID();
  }

  const bytes: number[] = [];
  if (c && typeof c.getRandomValues === 'function') {
    const buf = new Uint8Array(16);
    c.getRandomValues(buf);
    for (let i = 0; i < 16; i += 1) bytes.push(buf[i] ?? 0);
  } else {
    for (let i = 0; i < 16; i += 1) bytes.push(Math.floor(Math.random() * 256));
  }
  // versão 4 + variante RFC 4122
  bytes[6] = ((bytes[6] ?? 0) & 0x0f) | 0x40;
  bytes[8] = ((bytes[8] ?? 0) & 0x3f) | 0x80;

  const hex = bytes.map((b) => b.toString(16).padStart(2, '0'));
  return [
    hex.slice(0, 4).join(''),
    hex.slice(4, 6).join(''),
    hex.slice(6, 8).join(''),
    hex.slice(8, 10).join(''),
    hex.slice(10, 16).join(''),
  ].join('-');
}
