'use client';

/** Cartão de crédito animado (vira ao focar o CVV). Puramente visual. */
function brand(num: string): string {
  const n = num.replace(/\D/g, '');
  if (/^4/.test(n)) return 'VISA';
  if (/^5[1-5]/.test(n) || /^2(2[2-9]|[3-6]|7[01]|720)/.test(n)) return 'Mastercard';
  if (/^3[47]/.test(n)) return 'Amex';
  if (/^(4011|4312|4389|438935|451416|457393|504175|5067|509|627780|636297|636368|65)/.test(n)) return 'Elo';
  if (/^(606282|3841)/.test(n)) return 'Hipercard';
  return '';
}

function groupNumber(num: string): string {
  const n = num.replace(/\D/g, '').slice(0, 19).padEnd(16, '•');
  return n.replace(/(.{4})/g, '$1 ').trim();
}

export function AnimatedCard({
  number,
  name,
  expiry,
  cvv,
  flipped,
}: {
  number: string;
  name: string;
  expiry: string;
  cvv: string;
  flipped: boolean;
}) {
  return (
    <div className="mx-auto w-full max-w-[340px] [perspective:1000px]">
      <div
        className={`relative aspect-[1.586/1] w-full rounded-xl text-white shadow-lg transition-transform duration-500 [transform-style:preserve-3d] ${
          flipped ? '[transform:rotateY(180deg)]' : ''
        }`}
      >
        {/* Frente */}
        <div className="absolute inset-0 flex flex-col justify-between rounded-xl bg-gradient-to-br from-gray-800 via-gray-900 to-black p-5 [backface-visibility:hidden]">
          <div className="flex items-start justify-between">
            <div className="h-8 w-11 rounded-md bg-gradient-to-br from-yellow-300 to-yellow-500" />
            <span className="text-sm font-semibold tracking-wide">{brand(number) || 'CARTÃO'}</span>
          </div>
          <div className="font-mono text-lg tracking-[0.15em] sm:text-xl">{groupNumber(number)}</div>
          <div className="flex items-end justify-between text-xs">
            <div className="min-w-0">
              <div className="text-[10px] uppercase text-white/60">Titular</div>
              <div className="truncate uppercase">{name || 'NOME NO CARTÃO'}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase text-white/60">Validade</div>
              <div>{expiry || 'MM/AA'}</div>
            </div>
          </div>
        </div>

        {/* Verso */}
        <div className="absolute inset-0 flex flex-col rounded-xl bg-gradient-to-br from-gray-800 via-gray-900 to-black [backface-visibility:hidden] [transform:rotateY(180deg)]">
          <div className="mt-5 h-10 w-full bg-black/80" />
          <div className="mx-5 mt-4 flex items-center gap-2">
            <div className="h-8 flex-1 rounded bg-white/90" />
            <div className="flex h-8 w-16 items-center justify-center rounded bg-white text-sm font-bold text-gray-900">
              {cvv || 'CVV'}
            </div>
          </div>
          <div className="mt-auto p-5 text-right text-xs font-semibold tracking-wide">
            {brand(number) || 'CARTÃO'}
          </div>
        </div>
      </div>
    </div>
  );
}
