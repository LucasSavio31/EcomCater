'use client';

import { useEffect, useRef, useState } from 'react';
import { Input } from '@ecom/ui';
import { centsToInput, inputToCents } from '@/lib/format';

interface CurrencyFieldProps {
  label?: string;
  /** Valor em centavos (ou null quando vazio). */
  cents: number | null | undefined;
  onChange: (cents: number | null) => void;
  hint?: string;
  placeholder?: string;
}

/**
 * Campo de dinheiro que NÃO reformata a cada tecla — o usuário digita à
 * vontade ("199,90", "1990", "19.9") e a conversão para centavos só acontece
 * ao sair do campo. Sincroniza com o valor de fora quando ele muda por outro
 * motivo (ex.: recarregar o formulário).
 */
export function CurrencyField({ label, cents, onChange, hint, placeholder }: CurrencyFieldProps) {
  const [text, setText] = useState(() => centsToInput(cents));
  const focused = useRef(false);

  useEffect(() => {
    if (!focused.current) setText(centsToInput(cents));
  }, [cents]);

  function commit(): void {
    focused.current = false;
    const c = inputToCents(text);
    onChange(c);
    setText(centsToInput(c)); // normaliza a exibição ("199,9" -> "199,90")
  }

  return (
    <div className="flex flex-col gap-1">
      <Input
        label={label}
        inputMode="decimal"
        placeholder={placeholder ?? '0,00'}
        value={text}
        onFocus={() => {
          focused.current = true;
        }}
        onChange={(e) => setText(e.target.value.replace(/[^\d.,]/g, ''))}
        onBlur={commit}
      />
      {hint && <p className="text-xs text-text-muted">{hint}</p>}
    </div>
  );
}
