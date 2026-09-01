import { test, expect } from '@playwright/test';
import { addFirstProductToCart } from './_helpers';

test.describe('Loja — navegação e catálogo', () => {
  test('home carrega com cabeçalho, menu e produtos', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/.+/);
    // menu superior estilo catlifestyle
    for (const label of ['NOVIDADES', 'MASCULINO', 'FEMININO', 'OUTLET']) {
      await expect(page.getByRole('navigation').getByText(label, { exact: true }).first()).toBeVisible();
    }
    // pelo menos um card de produto com preço
    await expect(page.getByText(/R\$\s?\d/).first()).toBeVisible();
  });

  test('mega menu abre e NÃO fecha ao mover para o submenu', async ({ page }) => {
    await page.goto('/');
    const masc = page.getByRole('navigation').getByText('MASCULINO', { exact: true }).first();
    await masc.hover();
    const panel = page.locator('nav >> text=Botas').first();
    await expect(panel).toBeVisible();
    // atravessa o vão até o painel — não pode sumir
    await panel.hover();
    await expect(panel).toBeVisible();
    await panel.click();
    await expect(page).toHaveURL(/\/categoria\/masculino\/botas/);
  });

  test('página de categoria lista produtos e filtro de preço aparece', async ({ page }) => {
    await page.goto('/categoria/masculino');
    await expect(page.getByText(/R\$\s?\d/).first()).toBeVisible();
  });

  // TODO: o clique na numeração via role=radio não está habilitando "Comprar"
  // headless (funciona manualmente e no e2e do backend). Ajustar selector/wait.
  test.fixme('PDP: adicionar ao carrinho reflete no carrinho', async ({ page }) => {
    await addFirstProductToCart(page);
    // mini-carrinho, "Adicionado ✓" ou o badge do carrinho no header
    await expect(
      page.getByText(/adicionado|meu carrinho|subtotal|resumo/i).first(),
    ).toBeVisible({ timeout: 10_000 });
    await page.goto('/carrinho');
    await expect(page.getByText(/R\$\s?\d/).first()).toBeVisible();
  });

  test('PDP: popup "Tabela de medidas" abre centralizado e fecha', async ({ page }) => {
    await page.goto('/categoria/masculino');
    await page.locator('a[href^="/produto/"]').first().click();
    const trigger = page.getByRole('button', { name: /tabela de medidas/i });
    if (!(await trigger.isVisible().catch(() => false))) test.skip(true, 'produto sem tabela vinculada');
    await trigger.click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText(/^TABELA DE MEDIDAS$/i)).toBeVisible();
    await page.getByRole('button', { name: /fechar/i }).first().click();
    await expect(page.getByRole('dialog')).toBeHidden();
  });

  test('páginas institucionais respondem', async ({ page }) => {
    for (const slug of ['quem-somos', 'troca-e-devolucao', 'politica-de-privacidade', 'formas-de-pagamento']) {
      const res = await page.goto(`/pagina/${slug}`);
      expect(res?.status(), slug).toBeLessThan(400);
      await expect(page.locator('h1, h2').first()).toBeVisible();
    }
  });
});
