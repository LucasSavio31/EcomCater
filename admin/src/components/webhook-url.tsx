'use client';

import { useState } from 'react';
import { Button } from '@ecom/ui';

/** Caixa read-only com a URL de webhook + botão copiar. */
export function WebhookUrlBox({ url, note }: { url?: string; note?: string }) {
  const [copied, setCopied] = useState(false);
  if (!url) return null;
  return (
    <div className="flex flex-col gap-1 rounded-card bg-bg-subtle p-3">
      <span className="text-xs font-semibold uppercase tracking-wide text-text-muted">
        URL de webhook — cadastre no painel do provedor
      </span>
      <div className="flex flex-wrap items-center gap-2">
        <code className="min-w-0 flex-1 break-all rounded border border-surface-border bg-surface px-2 py-1 text-xs">
          {url}
        </code>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            void navigator.clipboard.writeText(url).then(() => {
              setCopied(true);
              window.setTimeout(() => setCopied(false), 2000);
            });
          }}
        >
          {copied ? 'Copiado ✓' : 'Copiar'}
        </Button>
      </div>
      {note && <span className="text-xs text-text-muted">{note}</span>}
    </div>
  );
}
