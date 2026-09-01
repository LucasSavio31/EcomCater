/** Ícones das formas de pagamento (PIX / cartão / boleto). Puramente visuais. */

type Method = 'pix' | 'credit_card' | 'boleto';

function PixIcon() {
  return (
    <svg viewBox="0 0 16 16" width="22" height="22" aria-hidden="true">
      <path
        fill="currentColor"
        d="M11.917 11.71a2.046 2.046 0 0 1-1.454-.602l-2.1-2.1a.4.4 0 0 0-.551 0l-2.108 2.108a2.046 2.046 0 0 1-1.454.602h-.414l2.66 2.66c.83.83 2.177.83 3.007 0l2.664-2.664h-.25ZM4.25 4.29c.55 0 1.067.214 1.454.602l2.11 2.11a.39.39 0 0 0 .55 0l2.1-2.1a2.046 2.046 0 0 1 1.453-.602h.25L9.503 1.638a2.126 2.126 0 0 0-3.007 0L3.836 4.291h.414ZM14.36 6.496 12.75 4.888a.31.31 0 0 1-.114.022h-.717c-.4 0-.784.16-1.068.443l-2.1 2.1a1.005 1.005 0 0 1-1.42 0l-2.11-2.11a1.51 1.51 0 0 0-1.068-.443h-.883a.31.31 0 0 1-.107-.02L1.64 6.496a2.126 2.126 0 0 0 0 3.007l1.622 1.612a.31.31 0 0 1 .107-.02h.883c.4 0 .784-.16 1.068-.443l2.11-2.11a1.032 1.032 0 0 1 1.42 0l2.1 2.1c.284.284.667.443 1.068.443h.717a.31.31 0 0 1 .114.022l1.61-1.61a2.126 2.126 0 0 0 0-3.008"
      />
    </svg>
  );
}

function CardIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="22"
      height="22"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      aria-hidden="true"
    >
      <rect x="2.5" y="5" width="19" height="14" rx="2.5" />
      <path d="M2.5 9.5h19" />
      <path d="M6 15h4" strokeLinecap="round" />
    </svg>
  );
}

function BoletoIcon() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true">
      <rect x="3" y="5" width="1.6" height="14" />
      <rect x="6" y="5" width="1" height="14" />
      <rect x="8.6" y="5" width="2" height="14" />
      <rect x="12" y="5" width="1" height="14" />
      <rect x="14.6" y="5" width="2.2" height="14" />
      <rect x="18" y="5" width="1" height="14" />
      <rect x="20.4" y="5" width="1.3" height="14" />
    </svg>
  );
}

export function PaymentIcon({ method }: { method: Method }) {
  if (method === 'pix') return <PixIcon />;
  if (method === 'credit_card') return <CardIcon />;
  return <BoletoIcon />;
}
