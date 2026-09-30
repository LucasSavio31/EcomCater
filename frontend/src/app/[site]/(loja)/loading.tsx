import { Spinner } from '@ecom/ui';

// Altura de tela cheia de propósito: o fallback sai antes do conteúdo no
// streaming. Baixo, ele deixava o rodapé visível no meio da tela, e o rodapé
// "pulava" ~500px pra baixo quando a página chegava (CLS 0,5–0,98 no
// Lighthouse). Assim o rodapé já nasce abaixo da dobra.
export default function Loading() {
  return (
    <div className="flex min-h-dvh justify-center py-20">
      <Spinner size="lg" label="Carregando…" />
    </div>
  );
}
