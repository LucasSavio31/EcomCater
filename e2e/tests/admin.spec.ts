import { test, expect } from '@playwright/test';

const EMAIL = process.env.E2E_ADMIN_EMAIL ?? 'admin@lojateste.com';
const PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? 'admin12345';

async function login(page: import('@playwright/test').Page) {
  await page.goto('/administracao/login');
  if (!/\/login/.test(page.url())) return; // já logado (sessão reaproveitada)
  await page.getByLabel(/e-?mail/i).fill(EMAIL);
  await page.getByLabel(/senha/i).fill(PASSWORD);
  await page.getByRole('button', { name: /entrar/i }).click();
  // espera SAIR da tela de login (não basta a URL conter /administracao)
  await expect(page).not.toHaveURL(/\/login/, { timeout: 15_000 });
  await expect(page.getByRole('button', { name: /entrar/i })).toHaveCount(0);
}

test.describe('Admin', () => {
  test('login e dashboard', async ({ page }) => {
    await login(page);
    await expect(page.getByText(/painel|dashboard|visão geral/i).first()).toBeVisible();
  });

  test('navegação pelos menus principais responde', async ({ page }) => {
    await login(page);
    const rotas = [
      '/administracao/produtos',
      '/administracao/categorias',
      '/administracao/pedidos',
      '/administracao/clientes',
      '/administracao/aparencia',
      '/administracao/tabelas-medidas',
      '/administracao/minha-conta',
      '/administracao/infraestrutura',
      '/administracao/newsletter',
    ];
    for (const r of rotas) {
      const res = await page.goto(r);
      expect(res?.status(), r).toBeLessThan(400);
      await expect(page.locator('h1, h2').first()).toBeVisible();
    }
  });

  test('infraestrutura: saúde dos serviços e aba de backup', async ({ page }) => {
    await login(page);
    await page.goto('/administracao/infraestrutura');
    await expect(page.getByText(/banco de dados/i).first()).toBeVisible();
    await page.getByRole('tab', { name: /backup/i }).click();
    await expect(page.getByText(/backup automático/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /fazer backup agora/i })).toBeVisible();
  });

  test('minha conta: 2FA visível', async ({ page }) => {
    await login(page);
    await page.goto('/administracao/minha-conta');
    await expect(page.getByText(/verificação em duas etapas/i).first()).toBeVisible();
  });

  test('tabelas de medidas: form começa fechado, abre no "+ Nova tabela"', async ({ page }) => {
    await login(page);
    await page.goto('/administracao/tabelas-medidas');
    await expect(page.getByRole('heading', { name: /^Nova tabela$/ })).toHaveCount(0);
    await page.getByRole('button', { name: /\+ nova tabela/i }).click();
    await expect(page.getByRole('heading', { name: /^Nova tabela$/ })).toBeVisible();
  });

  test('proteção: excluir pedido exige confirmação/estado cancelado', async ({ page, request }) => {
    await login(page);
    // via API, com o token da sessão do admin
    const raw = await page.evaluate(() => localStorage.getItem('ecom.admin.session'));
    const token = raw ? JSON.parse(raw).accessToken : null;
    expect(token).toBeTruthy();
    const list = await request.get('http://localhost:8000/api/admin/orders?page_size=1', {
      headers: { authorization: `Bearer ${token}` },
    });
    const items = (await list.json()).items ?? [];
    test.skip(items.length === 0, 'sem pedidos para testar a proteção');
    const number = items[0].number;
    const del = await request.delete(`http://localhost:8000/api/admin/orders/${number}`, {
      headers: { authorization: `Bearer ${token}` },
    });
    // nunca 204: sem confirm=true e/ou pedido não cancelado → 4xx
    expect(del.status(), `status ${del.status()}`).toBeGreaterThanOrEqual(400);
    expect(del.status()).toBeLessThan(500);
  });
});
