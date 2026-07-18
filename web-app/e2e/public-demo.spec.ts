import {expect, test} from '@playwright/test';

test('teaches selection, approval, retry, and multi-agent success', async ({page}) => {
  await page.goto('/');
  await expect(page.getByRole('heading', {name: 'The Reviewer needs you.'})).toBeVisible();
  await expect(page.locator('.matrixPad')).toHaveCount(64);
  await expect(page.locator('.sceneControl')).toHaveCount(8);
  await expect(page.locator('.railControl')).toHaveCount(8);

  await page.getByRole('button', {name: 'Select Reviewer'}).first().click();
  await expect(page.getByRole('heading', {name: 'Approve the review.'})).toBeVisible();
  await page.getByRole('button', {name: 'Approve'}).click();

  await page.getByRole('button', {name: 'Select Tests'}).first().click();
  await expect(page.getByRole('heading', {name: 'Retry the test agent.'})).toBeVisible();
  await page.getByRole('button', {name: 'Retry'}).click();

  await expect(page.getByRole('heading', {name: 'The agents form a constellation.'})).toBeVisible();
  await expect(page.getByRole('button', {name: 'Sandbox'})).toBeEnabled();
});

test('keeps the controller inside the viewport', async ({page}) => {
  await page.goto('/');
  const metrics = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(metrics.scroll).toBeLessThanOrEqual(metrics.viewport);
  await expect(page.locator('.virtualSurface')).toBeVisible();
});
