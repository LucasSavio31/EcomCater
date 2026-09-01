import { test, expect } from '@playwright/test';
import { addFirstProductToCart } from './_helpers';

/**
 * Smoke do checkout pela UI: chega ao checkout com item e o formulário aparece.
 * O fluxo completo (pedido criado + e-mails + linha do tempo) é coberto pelo
 * e2e do backend (pytest `test_purchase_flow`) e pelo script de validação ao vivo.
 */
// depende do helper addFirstProductToCart (mesmo ajuste pendente do store.spec)
test.fixme('carrinho → checkout: formulário de identificação aparece', async ({ page }) => {
  await addFirstProductToCart(page);

  await page.goto('/carrinho');
  await expect(page.getByText(/R\$\s?\d/).first()).toBeVisible();
  await page.getByRole('button', { name: /finalizar compra/i }).click();

  await expect(page).toHaveURL(/\/checkout/);
  await expect(page.getByText(/identifica|e-?mail|dados de contato/i).first()).toBeVisible();
  // sem rolagem horizontal (mobile e desktop)
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  );
  expect(overflow).toBeFalsy();
});
