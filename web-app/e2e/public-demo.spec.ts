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
  await expect(page.locator('.virtualSurface')).toBeVisible();
  const metrics = await page.evaluate(() => {
    const surface = document.querySelector('.virtualSurface')?.getBoundingClientRect();
    const modes = document.querySelector('.modeSwitch')?.getBoundingClientRect();
    return {
      viewport: document.documentElement.clientWidth,
      scroll: document.documentElement.scrollWidth,
      surface: surface ? {left: surface.left, right: surface.right} : null,
      modes: modes ? {left: modes.left, right: modes.right} : null,
    };
  });
  expect(metrics.scroll).toBeLessThanOrEqual(metrics.viewport);
  expect(metrics.surface?.left).toBeGreaterThanOrEqual(0);
  expect(metrics.surface?.right).toBeLessThanOrEqual(metrics.viewport);
  expect(metrics.modes?.left).toBeGreaterThanOrEqual(0);
  expect(metrics.modes?.right).toBeLessThanOrEqual(metrics.viewport);
});
