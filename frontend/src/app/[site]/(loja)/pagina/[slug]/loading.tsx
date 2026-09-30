import { Spinner } from '@ecom/ui';

// tela cheia: rodapé abaixo da dobra até o conteúdo chegar (CLS) — ver (loja)/loading.tsx
export default function Loading() {
  return (
    <div className="flex min-h-dvh justify-center py-16">
      <Spinner size="lg" label="Carregando página…" />
    </div>
  );
}
