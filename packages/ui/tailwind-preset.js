/**
 * Preset Tailwind compartilhado (loja + admin).
 *
 * As cores e a fonte referenciam CSS variables — o tema real vem do banco
 * (`GET /api/theme`) e é injetado no SSR como `<style>:root{...}</style>`.
 * Trocar cor/logo/fonte no admin reflete sem rebuild.
 *
 * Fallbacks (paleta neutra) ficam em `src/tokens/base.css`.
 *
 * @type {import('tailwindcss').Config}
 */
module.exports = {
  darkMode: 'class',
  theme: {
    // Mobile-first: cada breakpoint é um min-width (do menor para o maior).
    screens: {
      sm: '480px',
      md: '768px',
      lg: '1024px',
      xl: '1280px',
      '2xl': '1536px',
    },
    extend: {
      colors: {
        primary: {
          DEFAULT: 'var(--color-primary)',
          fg: 'var(--color-primary-fg)',
        },
        secondary: {
          DEFAULT: 'var(--color-secondary)',
          fg: 'var(--color-secondary-fg)',
        },
        accent: {
          DEFAULT: 'var(--color-accent)',
          fg: 'var(--color-accent-fg)',
        },
        bg: {
          DEFAULT: 'var(--color-bg)',
          subtle: 'var(--color-bg-subtle)',
        },
        surface: {
          DEFAULT: 'var(--color-surface)',
          border: 'var(--color-border)',
        },
        text: {
          DEFAULT: 'var(--color-text)',
          muted: 'var(--color-text-muted)',
        },
        success: 'var(--color-success)',
        warning: 'var(--color-warning)',
        danger: 'var(--color-danger)',
      },
      fontFamily: {
        sans: 'var(--font-family)',
      },
      borderRadius: {
        // Cards e superfícies são sempre arredondados — nunca `rounded-none`.
        card: 'var(--radius-card)',
      },
      minHeight: {
        touch: '44px',
      },
      minWidth: {
        touch: '44px',
      },
      ringColor: {
        DEFAULT: 'var(--color-accent)',
      },
    },
  },
  plugins: [],
};
