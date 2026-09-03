'use client';

import { useEffect, useRef } from 'react';
import type { RefObject } from 'react';

const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

interface Options {
  active: boolean;
  onEscape?: () => void;
  /** Elemento que recebe o foco ao fechar (default: o que estava focado ao abrir). */
  returnFocusTo?: HTMLElement | null;
}

/**
 * Prende o foco dentro de `containerRef` enquanto `active`, trata Tab/Shift+Tab
 * circularmente, dispara `onEscape` no Esc e devolve o foco ao fechar.
 */
export function useFocusTrap(
  containerRef: RefObject<HTMLElement | null>,
  { active, onEscape, returnFocusTo }: Options,
): void {
  // Guarda os callbacks/opções mutáveis em refs: o efeito abaixo só deve
  // (re)rodar quando `active` muda — não a cada render do pai. Sem isso, um
  // `onClose={() => ...}` inline fazia o trap re-inicializar e ROUBAR o foco
  // do input a cada tecla digitada dentro de um Modal.
  const onEscapeRef = useRef(onEscape);
  onEscapeRef.current = onEscape;
  const returnFocusRef = useRef(returnFocusTo);
  returnFocusRef.current = returnFocusTo;

  useEffect(() => {
    if (!active) return;
    const container = containerRef.current;
    if (!container) return;

    const previouslyFocused = (returnFocusRef.current ?? document.activeElement) as
      | HTMLElement
      | null;

    const focusFirst = (): void => {
      const first = container.querySelector<HTMLElement>(FOCUSABLE);
      (first ?? container).focus();
    };
    focusFirst();

    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') {
        event.stopPropagation();
        onEscapeRef.current?.();
        return;
      }
      if (event.key !== 'Tab') return;

      const items = Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => el.offsetParent !== null || el === document.activeElement,
      );
      if (items.length === 0) {
        event.preventDefault();
        container.focus();
        return;
      }
      const first = items[0]!;
      const last = items[items.length - 1]!;
      const activeEl = document.activeElement as HTMLElement | null;

      if (event.shiftKey && (activeEl === first || !container.contains(activeEl))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && activeEl === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', onKeyDown, true);
    return () => {
      document.removeEventListener('keydown', onKeyDown, true);
      previouslyFocused?.focus?.();
    };
  }, [active, containerRef]);
}
