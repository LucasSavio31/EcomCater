/** Ícones do menu — traço fino, monocromático (currentColor). */
import type { SVGProps } from 'react';

type P = SVGProps<SVGSVGElement>;
const base = (p: P) => ({
  width: 18,
  height: 18,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.6,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  ...p,
});

export const IconDashboard = (p: P) => (
  <svg {...base(p)}>
    <rect x="3" y="3" width="8" height="8" rx="1" />
    <rect x="13" y="3" width="8" height="5" rx="1" />
    <rect x="13" y="10" width="8" height="11" rx="1" />
    <rect x="3" y="13" width="8" height="8" rx="1" />
  </svg>
);
export const IconProducts = (p: P) => (
  <svg {...base(p)}>
    <path d="M21 8 12 3 3 8l9 5 9-5Z" />
    <path d="M3 8v8l9 5 9-5V8" />
    <path d="M12 13v8" />
  </svg>
);
export const IconCategories = (p: P) => (
  <svg {...base(p)}>
    <path d="M3 7h18M3 12h18M3 17h18" />
    <circle cx="6" cy="7" r="0.5" fill="currentColor" />
  </svg>
);
export const IconOrders = (p: P) => (
  <svg {...base(p)}>
    <path d="M8 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2h-2" />
    <rect x="8" y="2" width="8" height="4" rx="1" />
    <path d="M9 12h6M9 16h4" />
  </svg>
);
export const IconCustomers = (p: P) => (
  <svg {...base(p)}>
    <circle cx="9" cy="8" r="3" />
    <path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" />
    <path d="M16 6a3 3 0 0 1 0 6M21 20c0-2.5-1.5-4.6-3.7-5.5" />
  </svg>
);
export const IconPromotions = (p: P) => (
  <svg {...base(p)}>
    <path d="M20.6 12.6 12 21l-8-8a4.5 4.5 0 0 1 0-6.4 4.5 4.5 0 0 1 6.4 0L12 8l1.6-1.6a4.5 4.5 0 0 1 6.4 6.2Z" />
  </svg>
);
export const IconPayment = (p: P) => (
  <svg {...base(p)}>
    <rect x="2" y="5" width="20" height="14" rx="2" />
    <path d="M2 10h20M6 15h4" />
  </svg>
);
export const IconShipping = (p: P) => (
  <svg {...base(p)}>
    <path d="M3 7h11v8H3zM14 10h4l3 3v2h-7" />
    <circle cx="7" cy="17" r="2" />
    <circle cx="17" cy="17" r="2" />
  </svg>
);
export const IconAnalytics = (p: P) => (
  <svg {...base(p)}>
    <path d="M4 20V10M10 20V4M16 20v-6M22 20H2" />
  </svg>
);
export const IconAppearance = (p: P) => (
  <svg {...base(p)}>
    <circle cx="12" cy="12" r="9" />
    <circle cx="8.5" cy="9.5" r="1.2" fill="currentColor" stroke="none" />
    <circle cx="15.5" cy="9.5" r="1.2" fill="currentColor" stroke="none" />
    <circle cx="9" cy="15" r="1.2" fill="currentColor" stroke="none" />
  </svg>
);
export const IconCheckout = (p: P) => (
  <svg {...base(p)}>
    <path d="M3 6h2l2.4 11.4A1 1 0 0 0 8.4 18h9a1 1 0 0 0 1-.8L20 8H6" />
    <path d="m9 12 2 2 4-4" />
  </svg>
);
export const IconSeals = (p: P) => (
  <svg {...base(p)}>
    <path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z" />
    <path d="m9 12 2 2 4-4" />
  </svg>
);
export const IconMenus = (p: P) => (
  <svg {...base(p)}>
    <path d="M4 6h16M4 12h16M4 18h10" />
  </svg>
);
export const IconModules = (p: P) => (
  <svg {...base(p)}>
    <rect x="3" y="3" width="7" height="7" rx="1" />
    <rect x="14" y="3" width="7" height="7" rx="1" />
    <rect x="3" y="14" width="7" height="7" rx="1" />
    <path d="M17.5 14v7M14 17.5h7" />
  </svg>
);
export const IconMail = (p: P) => (
  <svg {...base(p)}>
    <rect x="3" y="5" width="18" height="14" rx="2" />
    <path d="m3 7 9 6 9-6" />
  </svg>
);
export const IconUsers = (p: P) => (
  <svg {...base(p)}>
    <circle cx="12" cy="8" r="3.5" />
    <path d="M5 20c0-3.9 3.1-7 7-7s7 3.1 7 7" />
  </svg>
);
export const IconFilters = (p: P) => (
  <svg {...base(p)}>
    <path d="M3 5h18l-7 8v6l-4-2v-4L3 5Z" />
  </svg>
);
export const IconLeads = (p: P) => (
  <svg {...base(p)}>
    <path d="M4 4h16v12H7l-3 3V4Z" />
    <path d="M8 9h8M8 12h5" />
  </svg>
);
export const IconStar = (p: P) => (
  <svg {...base(p)}>
    <path d="m12 3 2.9 5.9 6.5.9-4.7 4.6 1.1 6.5L12 17.8 6.2 21l1.1-6.5L2.6 9.8l6.5-.9L12 3Z" />
  </svg>
);
export const IconEdit = (p: P) => (
  <svg {...base(p)}>
    <path d="M12 20h9" />
    <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5Z" />
  </svg>
);
export const IconTrash = (p: P) => (
  <svg {...base(p)}>
    <path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14" />
    <path d="M10 11v6M14 11v6" />
  </svg>
);
export const IconPrinter = (p: P) => (
  <svg {...base(p)}>
    <path d="M6 9V3h12v6" />
    <rect x="3" y="9" width="18" height="8" rx="2" />
    <path d="M6 14h12v7H6z" />
  </svg>
);
export const IconTag = (p: P) => (
  <svg {...base(p)}>
    <path d="M20.6 12.6 12 21l-8-8a4.5 4.5 0 0 1 0-6.4l4-4H21v13.6a4.5 4.5 0 0 1-.4 0Z" />
    <circle cx="15.5" cy="8.5" r="1.5" />
  </svg>
);
export const IconCart = (p: P) => (
  <svg {...base(p)}>
    <path d="M3 4h2l2.4 12.3a1 1 0 0 0 1 .8h9.2a1 1 0 0 0 1-.8L21 8H6" />
    <circle cx="9" cy="20" r="1.4" />
    <circle cx="18" cy="20" r="1.4" />
  </svg>
);
export const IconRuler = (p: P) => (
  <svg {...base(p)}>
    <path d="M4 15 15 4l5 5L9 20z" />
    <path d="M8 11l2 2M11 8l2 2M14 5l2 2M5 14l2 2" />
  </svg>
);
