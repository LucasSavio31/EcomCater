import { test, expect } from '@playwright/test';
import { addFirstProductToCart } from './_helpers';

/** Roda no projeto `store-mobile` (viewport Pixel 7). */
test.describe('Loja no mobile', () => {
  test('home sem rolagem horizontal', async ({ page }) => {
    await page.goto('/');
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(overflow, 'body não deve rolar na horizontal').toBeFalsy();
  });

  test('rodapé visível no mobile (sanfona)', async ({ page }) => {
    await page.goto('/');
    const footer = page.locator('footer');
    await footer.scrollIntoViewIfNeeded();
    await expect(footer).toBeVisible();
    // no mobile as seções ficam em <details> (sanfona) — abrir a primeira
    const firstAccordion = footer.locator('details, summary').first();
    if (await firstAccordion.count()) {
      await firstAccordion.click().catch(() => {});
    }
    await expect(footer).toContainText(/institucional|ajuda|categorias|quem somos/i);
  });

  test.fixme('checkout: sem rolagem horizontal', async ({ page }) => {
    await addFirstProductToCart(page);
    await page.goto('/checkout');
    await page.waitForLoadState('networkidle');
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(overflow).toBeFalsy();
  });
});
