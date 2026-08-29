/** Bandeiras de pagamento — SVGs inline simples (sem dependência externa). */

const FLAGS = ['Visa', 'Master', 'Amex', 'Elo', 'Hipercard', 'Pix', 'Boleto'] as const;

export function PaymentFlags() {
  return (
    <ul className="flex flex-wrap items-center gap-1.5" aria-label="Formas de pagamento aceitas">
      {FLAGS.map((flag) => (
        <li key={flag}>
          <span
            className="inline-flex h-6 min-w-[38px] items-center justify-center rounded-[4px] border border-surface-border bg-surface px-1 text-[9px] font-semibold uppercase tracking-wide text-text-muted"
            title={flag}
          >
            {flag}
          </span>
        </li>
      ))}
    </ul>
  );
}
