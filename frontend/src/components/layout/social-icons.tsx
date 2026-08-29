import type { ReactElement, SVGProps } from 'react';

type IconProps = SVGProps<SVGSVGElement>;

function InstagramIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true" {...props}>
      <rect x="3" y="3" width="18" height="18" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}

function FacebookIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...props}>
      <path d="M13.5 21v-7h2.4l.4-3h-2.8V9c0-.9.3-1.5 1.6-1.5H16.5V4.8C16.2 4.8 15.2 4.7 14 4.7c-2.4 0-4 1.5-4 4.2V11H7.5v3H10v7h3.5Z" />
    </svg>
  );
}

function TiktokIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...props}>
      <path d="M16 3c.3 2.1 1.6 3.7 3.7 4v2.5c-1.3.1-2.6-.3-3.7-1v6.7A6.2 6.2 0 1 1 10 9.2v2.7a3.5 3.5 0 1 0 2.5 3.4V3H16Z" />
    </svg>
  );
}

function YoutubeIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...props}>
      <path d="M21.6 8s-.2-1.4-.8-2c-.7-.8-1.6-.8-2-.9C16 4.8 12 4.8 12 4.8s-4 0-6.8.3c-.4 0-1.3 0-2 .9-.6.6-.8 2-.8 2S2.2 9.6 2.2 11.3v1.4C2.2 14.4 2.4 16 2.4 16s.2 1.4.8 2c.7.8 1.7.8 2.1.9 1.5.1 6.7.2 6.7.2s4 0 6.8-.3c.4 0 1.3 0 2-.9.6-.6.8-2 .8-2s.2-1.7.2-3.4v-1.4C21.8 9.6 21.6 8 21.6 8ZM10 14.5v-5l4.2 2.5-4.2 2.5Z" />
    </svg>
  );
}

const MAP: Record<string, (p: IconProps) => ReactElement> = {
  instagram: InstagramIcon,
  facebook: FacebookIcon,
  tiktok: TiktokIcon,
  youtube: YoutubeIcon,
};

export interface SocialLink {
  network: string;
  url: string;
}

export function SocialIcons({ links }: { links: SocialLink[] }) {
  if (links.length === 0) return null;
  return (
    <ul className="flex items-center gap-2">
      {links.map((link) => {
        const Icon = MAP[link.network.toLowerCase()] ?? InstagramIcon;
        return (
          <li key={link.network}>
            <a
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={link.network}
              className="inline-flex min-h-touch min-w-touch items-center justify-center rounded-card border border-surface-border p-2 hover:border-primary"
            >
              <Icon className="h-5 w-5" />
            </a>
          </li>
        );
      })}
    </ul>
  );
}
