import type { SVGProps } from 'react';

/** Ícones de linha (stroke currentColor). Decorativos por padrão (aria-hidden). */

type IconProps = SVGProps<SVGSVGElement>;

function base(props: IconProps) {
  return {
    width: 24,
    height: 24,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.6,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    'aria-hidden': true,
    focusable: false,
    ...props,
  };
}

export function SearchIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </svg>
  );
}

export function HeartIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 20s-7-4.3-9.3-8.5C1.2 8.7 2.6 5.5 5.8 5.1 8 4.8 9.7 6 12 8.3 14.3 6 16 4.8 18.2 5.1c3.2.4 4.6 3.6 3.1 6.4C19 15.7 12 20 12 20Z" />
    </svg>
  );
}

export function UserIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 20c1.5-4 5-6 8-6s6.5 2 8 6" />
    </svg>
  );
}

export function BagIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M6 8h12l1 12H5L6 8Z" />
      <path d="M9 8V6a3 3 0 0 1 6 0v2" />
    </svg>
  );
}

export function HeadsetIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M4 13v-1a8 8 0 0 1 16 0v1" />
      <path d="M4 13h2.5A1.5 1.5 0 0 1 8 14.5v3A1.5 1.5 0 0 1 6.5 19H6a2 2 0 0 1-2-2Z" />
      <path d="M20 13h-2.5a1.5 1.5 0 0 0-1.5 1.5v3a1.5 1.5 0 0 0 1.5 1.5h.5a2 2 0 0 0 2-2Z" />
      <path d="M20 17v1a3 3 0 0 1-3 3h-3" />
    </svg>
  );
}

export function MenuIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  );
}

export function CloseIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M6 6l12 12M18 6 6 18" />
    </svg>
  );
}

export function ChevronDownIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

export function ChevronRightIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="m9 6 6 6-6 6" />
    </svg>
  );
}

export function ChevronLeftIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="m15 6-6 6 6 6" />
    </svg>
  );
}

export function WhatsappIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M4 20l1.4-4A8 8 0 1 1 9 18.6L4 20Z" />
      <path d="M9 9.5c0 3 2.5 5.5 5.5 5.5.7 0 1.2-.6 1.2-1.2 0-.3-.1-.5-.3-.7l-1.2-1c-.3-.2-.6-.2-.9 0l-.5.4c-1-.5-1.8-1.3-2.3-2.3l.4-.5c.2-.3.2-.6 0-.9l-1-1.2a.9.9 0 0 0-.7-.3c-.6 0-1.2.5-1.2 1.2Z" />
    </svg>
  );
}
