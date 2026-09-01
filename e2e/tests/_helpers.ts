import { expect, type Page } from '@playwright/test';

/** Abre a PDP do 1º produto de uma categoria, escolhe a 1ª numeração disponível
 * em cada eixo de variação e adiciona ao carrinho. Deixa a página na PDP. */
export async function addFirstProductToCart(page: Page, category = 'masculino'): Promise<void> {
  await page.goto(`/categoria/${category}`);
  await page.locator('main a[href^="/produto/"]').first().click();
  await page.waitForURL(/\/produto\//);

  // um clique na 1ª opção disponível de cada radiogroup (Numeração, Cor, ...)
  const groups = page.locator('[role="radiogroup"]');
  const gcount = await groups.count();
  for (let g = 0; g < gcount; g++) {
    const options = groups.nth(g).getByRole('radio');
    const ocount = await options.count();
    for (let i = 0; i < ocount; i++) {
      const opt = options.nth(i);
      if ((await opt.getAttribute('aria-disabled')) !== 'true') {
        await opt.click();
        await expect(opt).toHaveAttribute('aria-checked', 'true');
        break;
      }
    }
  }

  const buy = page.getByRole('button', { name: /comprar/i });
  await expect(buy).toBeEnabled({ timeout: 15_000 });
  await buy.click();
}
