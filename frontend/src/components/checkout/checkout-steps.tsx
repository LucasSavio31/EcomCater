'use client';

/** Linha do tempo do checkout: 1 Identificação · 2 Dados · 3 Entrega · 4 Pagamento. */
export type CheckoutStepId = 'identify' | 'profile' | 'shipping' | 'payment';

const ORDER: CheckoutStepId[] = ['identify', 'profile', 'shipping', 'payment'];

const LABELS: Record<CheckoutStepId, string> = {
  identify: 'Identificação',
  profile: 'Dados',
  shipping: 'Entrega',
  payment: 'Pagamento',
};

export function CheckoutStepsTimeline({
  current,
  hasShipping = true,
  onJump,
  furthest,
  activeStyle,
}: {
  current: CheckoutStepId;
  hasShipping?: boolean;
  furthest: CheckoutStepId;
  onJump?: (id: CheckoutStepId) => void;
  /** Cores da bolinha da etapa ativa. */
  activeStyle?: { bg: string; fg: string };
}) {
  const steps = ORDER.filter((s) => (s === 'shipping' ? hasShipping : true));
  const idx = (id: CheckoutStepId) => steps.indexOf(id);
  const curIdx = idx(current);
  const maxIdx = idx(furthest);

  return (
    <ol className="mb-6 flex items-start">
      {steps.map((step, i) => {
        const done = i < curIdx;
        const active = i === curIdx;
        const reachable = i <= maxIdx;
        return (
          <li key={step} className="relative flex flex-1 flex-col items-center gap-1.5">
            {/* risquinho ligando esta bolinha à próxima (centralizado na altura da bolinha) */}
            {i < steps.length - 1 && (
              <span
                aria-hidden
                className={`absolute left-1/2 top-[13px] h-0.5 w-full ${
                  i < curIdx ? 'bg-success' : 'bg-surface-border'
                }`}
              />
            )}
            <button
              type="button"
              disabled={!reachable || !onJump}
              onClick={() => onJump?.(step)}
              className={`relative z-10 flex flex-col items-center gap-1.5 px-1 ${
                reachable && onJump ? 'cursor-pointer' : 'cursor-default'
              }`}
            >
              <span
                style={
                  active && activeStyle
                    ? { backgroundColor: activeStyle.bg, color: activeStyle.fg }
                    : undefined
                }
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                  active
                    ? activeStyle
                      ? ''
                      : 'bg-btn text-btn-fg'
                    : done
                      ? 'bg-success text-white'
                      : 'border border-surface-border bg-bg text-text-muted'
                }`}
              >
                {done ? '✓' : i + 1}
              </span>
              <span
                className={`text-center text-xs leading-tight sm:text-sm ${
                  active ? 'font-semibold text-text' : 'text-text-muted'
                }`}
              >
                {LABELS[step]}
              </span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
