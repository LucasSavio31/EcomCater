'use client';

import { useState } from 'react';
import type { ReactNode } from 'react';
import { Button, Modal } from '@ecom/ui';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: 'primary' | 'danger';
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  tone = 'primary',
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <Modal
      open={open}
      onClose={onCancel}
      title={title}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onCancel} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button variant={tone === 'danger' ? 'danger' : 'primary'} onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      {description && <div className="text-sm text-text-muted">{description}</div>}
    </Modal>
  );
}

/** Hook utilitário: guarda o alvo da confirmação e o estado de submissão. */
export function useConfirm<T>() {
  const [target, setTarget] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  return {
    target,
    loading,
    open: target !== null,
    ask: (value: T) => setTarget(value),
    cancel: () => {
      if (!loading) setTarget(null);
    },
    run: async (fn: (value: T) => Promise<void>) => {
      if (target === null) return;
      setLoading(true);
      try {
        await fn(target);
        setTarget(null);
      } finally {
        setLoading(false);
      }
    },
  };
}
