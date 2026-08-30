'use client';

/** Linha do tempo do checkout: 1 Dados pessoais · 2 Entrega · 3 Pagamento. */
export type CheckoutStepId = 'identify' | 'profile' | 'shipping' | 'payment';

const ORDER: CheckoutStepId[] = ['identify', 'profile', 'shipping', 'payment'];

const LABELS: Record<CheckoutStepId, string> = {
  identify: 'Identificação',
  profile: 'Dados pessoais',
  shipping: 'Entrega',
  payment: 'Pagamento',
};

export function CheckoutStepsTimeline({
  current,
  hasShipping = true,
  onJump,
  furthest,
}: {
  current: CheckoutStepId;
  hasShipping?: boolean;
  furthest: CheckoutStepId;
  onJump?: (id: CheckoutStepId) => void;
}) {
  const steps = ORDER.filter((s) => (s === 'shipping' ? hasShipping : true));
  const idx = (id: CheckoutStepId) => steps.indexOf(id);
  const curIdx = idx(current);
  const maxIdx = idx(furthest);

  return (
    <ol className="mb-6 flex items-center gap-2 text-sm">
      {steps.map((step, i) => {
        const done = i < curIdx;
        const active = i === curIdx;
        const reachable = i <= maxIdx;
        return (
          <li key={step} className="flex flex-1 items-center gap-2">
            <button
              type="button"
              disabled={!reachable || !onJump}
              onClick={() => onJump?.(step)}
              className={`flex min-w-0 items-center gap-2 ${reachable && onJump ? 'cursor-pointer' : 'cursor-default'}`}
            >
              <span
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                  active
                    ? 'bg-btn text-btn-fg'
                    : done
                      ? 'bg-success text-white'
                      : 'border border-surface-border text-text-muted'
                }`}
              >
                {done ? '✓' : i + 1}
              </span>
              <span
                className={`truncate ${active ? 'font-semibold text-text' : 'text-text-muted'}`}
              >
                {LABELS[step]}
              </span>
            </button>
            {i < steps.length - 1 && (
              <span className={`h-px flex-1 ${i < curIdx ? 'bg-success' : 'bg-surface-border'}`} />
            )}
          </li>
        );
      })}
    </ol>
  );
}
