'use client';

import { Input } from '@ecom/ui';
import { AsyncBoundary } from '@/components/async-boundary';
import { useThemeEditor } from './use-theme-editor';
import { ColorGrid, SaveBar, SectionCard, type ColorFieldDef } from './_shared';

const EMAIL: ColorFieldDef[] = [
  { key: 'email_header_bg_color', label: 'Fundo do cabeçalho' },
  { key: 'email_header_text_color', label: 'Texto do cabeçalho' },
  { key: 'email_body_bg_color', label: 'Fundo do corpo' },
  { key: 'email_text_color', label: 'Texto do corpo' },
  { key: 'email_button_color', label: 'Fundo do botão (CTA)' },
  { key: 'email_button_text_color', label: 'Texto do botão (CTA)' },
];

export function EmailsTab() {
  const { theme, dirty, saving, loading, error, reload, set, save, discard } = useThemeEditor();

  return (
    <AsyncBoundary loading={loading} error={error} onRetry={reload}>
      {theme && (
        <div className="flex max-w-3xl flex-col gap-6">
          <SectionCard
            title="E-mails transacionais"
            hint="Identidade visual dos e-mails (nova conta, pedido, pagamento, status). O envio usa o SMTP configurado em Sistema → E-mail (SMTP)."
          >
            <ColorGrid fields={EMAIL} theme={theme} set={set} cols={3} />
            <Input
              label="Texto do rodapé do e-mail"
              value={theme.email_footer_text}
              onChange={(e) => set('email_footer_text', e.target.value)}
            />
          </SectionCard>

          <SaveBar dirty={dirty} saving={saving} onSave={() => void save()} onDiscard={discard} />
        </div>
      )}
    </AsyncBoundary>
  );
}
