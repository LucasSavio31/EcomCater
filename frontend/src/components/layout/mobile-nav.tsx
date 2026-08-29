'use client';

import { useState } from 'react';
import Link from 'next/link';
import type { MenuItem } from '@/modules/menus/types';
import { ChevronDownIcon, HeadsetIcon, HeartIcon, UserIcon } from '@/components/icons';

interface MobileNavProps {
  items: MenuItem[];
  onNavigate: () => void;
  whatsappHref: string | null;
}

/** Conteúdo do drawer mobile: nav em acordeão + atalhos de conta/atendimento. */
export function MobileNav({ items, onNavigate, whatsappHref }: MobileNavProps) {
  return (
    <div className="flex flex-col gap-4">
      <span id="mobile-nav-title" className="sr-only">
        Menu de navegação
      </span>

      <ul className="flex flex-col divide-y divide-surface-border">
        {items.map((item) => (
          <MobileNavItem key={item.id} item={item} onNavigate={onNavigate} />
        ))}
      </ul>

      <div className="mt-2 flex flex-col gap-1 border-t border-surface-border pt-4">
        <Link
          href="/minha-conta"
          onClick={onNavigate}
          className="inline-flex min-h-touch items-center gap-2 rounded-card px-2 text-sm hover:bg-bg-subtle"
        >
          <UserIcon className="h-5 w-5" /> Minha conta
        </Link>
        <Link
          href="/minha-conta/favoritos"
          onClick={onNavigate}
          className="inline-flex min-h-touch items-center gap-2 rounded-card px-2 text-sm hover:bg-bg-subtle"
        >
          <HeartIcon className="h-5 w-5" /> Favoritos
        </Link>
        {whatsappHref && (
          <a
            href={whatsappHref}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex min-h-touch items-center gap-2 rounded-card px-2 text-sm hover:bg-bg-subtle"
          >
            <HeadsetIcon className="h-5 w-5" /> Atendimento
          </a>
        )}
      </div>
    </div>
  );
}

function MobileNavItem({ item, onNavigate }: { item: MenuItem; onNavigate: () => void }) {
  const [open, setOpen] = useState(false);
  const hasChildren = item.children.length > 0 || item.size_shortcuts.length > 0;

  if (!hasChildren) {
    return (
      <li>
        <Link
          href={item.url}
          onClick={onNavigate}
          className={`flex min-h-touch items-center px-2 text-sm font-medium ${
            item.highlight ? 'text-accent' : 'text-text'
          }`}
        >
          {item.label}
        </Link>
      </li>
    );
  }

  return (
    <li>
      <div className="flex items-center">
        <Link
          href={item.url}
          onClick={onNavigate}
          className={`flex min-h-touch flex-1 items-center px-2 text-sm font-medium ${
            item.highlight ? 'text-accent' : 'text-text'
          }`}
        >
          {item.label}
        </Link>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-label={`${open ? 'Recolher' : 'Expandir'} ${item.label}`}
          className="min-h-touch min-w-touch rounded-card p-1 text-text-muted"
        >
          <ChevronDownIcon className={`h-4 w-4 transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {open && (
        <div className="pb-3 pl-4">
          <ul className="flex flex-col gap-1">
            {item.children.map((col) => (
              <li key={col.id}>
                <Link
                  href={col.url}
                  onClick={onNavigate}
                  className="flex min-h-touch items-center text-sm font-medium text-text"
                >
                  {col.label}
                </Link>
                {col.children.length > 0 && (
                  <ul className="flex flex-col gap-0.5 pb-1 pl-3">
                    {col.children.map((leaf) => (
                      <li key={leaf.id}>
                        <Link
                          href={leaf.url}
                          onClick={onNavigate}
                          className="flex min-h-touch items-center text-sm text-text-muted"
                        >
                          {leaf.label}
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>

          {item.size_shortcuts.length > 0 && (
            <div className="mt-2">
              <p className="mb-1 text-xs font-semibold text-text">Compre por tamanho</p>
              <ul className="flex flex-wrap gap-2">
                {item.size_shortcuts.map((shortcut) => (
                  <li key={`${shortcut.label}-${shortcut.url}`}>
                    <Link
                      href={shortcut.url}
                      onClick={onNavigate}
                      className="inline-flex min-h-[40px] min-w-[40px] items-center justify-center rounded-card border border-surface-border px-2 text-sm"
                    >
                      {shortcut.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </li>
  );
}
