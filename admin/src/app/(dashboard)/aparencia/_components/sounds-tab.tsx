'use client';

import { Button } from '@ecom/ui';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox } from '@/components/form-controls';
import { playReturnSound, playSaleSound } from '@/lib/sounds';
import { useThemeEditor } from './use-theme-editor';
import { SaveBar, SectionCard } from './_shared';

export function SoundsTab() {
  const { theme, dirty, saving, loading, error, reload, set, save, discard } = useThemeEditor();

  return (
    <AsyncBoundary loading={loading} error={error} onRetry={reload}>
      {theme && (
        <div className="flex max-w-3xl flex-col gap-6">
          <SectionCard
            title="Som de venda"
            hint="Toca um som de caixa registradora no painel assim que um pedido é pago -- em qualquer tela, enquanto o admin estiver aberto."
          >
            <div className="flex items-center justify-between gap-4">
              <Checkbox
                label="Tocar som ao confirmar pagamento de uma venda"
                checked={theme.sound_sale_enabled}
                onChange={(v) => set('sound_sale_enabled', v)}
              />
              <Button size="sm" variant="outline" onClick={playSaleSound}>
                Testar som
              </Button>
            </div>
          </SectionCard>

          <SectionCard
            title="Som de devolução"
            hint="Toca um som quando a devolução de um pedido é marcada como entregue."
          >
            <div className="flex items-center justify-between gap-4">
              <Checkbox
                label="Tocar som ao receber uma devolução entregue"
                checked={theme.sound_return_enabled}
                onChange={(v) => set('sound_return_enabled', v)}
              />
              <Button size="sm" variant="outline" onClick={playReturnSound}>
                Testar som
              </Button>
            </div>
          </SectionCard>

          <SaveBar dirty={dirty} saving={saving} onSave={() => void save()} onDiscard={discard} />
        </div>
      )}
    </AsyncBoundary>
  );
}
