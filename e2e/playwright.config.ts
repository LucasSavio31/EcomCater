import { defineConfig, devices } from '@playwright/test';

/**
 * Testes end-to-end da loja (:3000) e do admin (:3001).
 *
 * Pré-requisitos: os três serviços no ar (API :8000, loja :3000, admin :3001)
 * com o seed aplicado (`python -m app.seed.run --catalog` + `app.seed.site_content`).
 *
 *   npm run test:e2e            # todos
 *   npm run test:e2e -- --ui    # modo interativo
 */
const STORE = process.env.E2E_STORE_URL ?? 'http://localhost:3000';
const ADMIN = process.env.E2E_ADMIN_URL ?? 'http://localhost:3001';

export default defineConfig({
  testDir: './tests',
  // o admin/loja rodam em modo dev (Next compila cada rota no 1º acesso), por
  // isso os tempos são folgados.
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  use: {
    baseURL: STORE,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    viewport: { width: 1280, height: 900 },
  },
  projects: [
    {
      name: 'store',
      testIgnore: /admin\.spec\.ts/,
      use: { ...devices['Desktop Chrome'], baseURL: STORE },
    },
    {
      name: 'store-mobile',
      testMatch: /responsive\.spec\.ts/,
      use: { ...devices['Pixel 7'], baseURL: STORE },
    },
    {
      name: 'admin',
      testMatch: /admin\.spec\.ts/,
      use: { ...devices['Desktop Chrome'], baseURL: ADMIN },
    },
  ],
});
