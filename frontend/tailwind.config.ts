import type { Config } from 'tailwindcss';
import uiPreset from '../packages/ui/tailwind-preset.js';

const config: Config = {
  presets: [uiPreset as Partial<Config>],
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
    '../packages/ui/src/**/*.{js,ts,jsx,tsx}',
  ],
};

export default config;
