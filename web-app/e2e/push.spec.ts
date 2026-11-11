import {expect, test} from '@playwright/test';

test('Push preview preserves selection, actions, demo and show', async ({page}, testInfo) => {
  await page.clock.install();
  await page.goto('/?surface=push');
  const push = page.getByLabel('Ableton Push 3 simulation', {exact: true});
  await expect(push).toBeVisible();
  await expect(push.locator('.matrixPad')).toHaveCount(64);
  await expect(push.locator('.sceneControl')).toHaveCount(8);
  await expect(push.locator('.railControl')).toHaveCount(8);
  await page.clock.runFor(6800);
  await expect(push.locator('.sceneControl.guidedControl')).toHaveAttribute('aria-label', 'Select Reviewer');
  await page.getByRole('button', {name: 'Sandbox', exact: true}).click();
  await push.getByRole('button', {name: 'Select Reviewer', exact: true}).click();
  await expect(push.getByRole('button', {name: 'Approve', exact: true})).toBeEnabled();
  await page.clock.runFor(300);
  await page.screenshot({path: testInfo.outputPath('push-dark.png'), fullPage: true});
  await page.getByRole('button', {name: 'Switch to light theme'}).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(page.viewportSize()!.width);
  await page.screenshot({path: testInfo.outputPath('push-light.png'), fullPage: true});
  await push.getByRole('button', {name: 'Approve', exact: true}).click();
  await expect(page.getByLabel('Reviewer state')).toHaveValue('running');
  await page.getByLabel('Surface', {exact: true}).selectOption('virtual');
  await expect(page.locator('.selectedReadout')).toContainText('Reviewer');
  await page.getByLabel('Surface', {exact: true}).selectOption('push');
  await page.getByRole('button', {name: 'Show', exact: true}).click();
  await page.getByRole('button', {name: 'Start Show', exact: true}).click();
  await page.clock.runFor(7000);
  await expect(push.locator('button:enabled')).toHaveCount(0);
  expect(await push.locator('.matrixPad').evaluateAll(pads =>
    pads.some(pad => getComputedStyle(pad).backgroundColor !== 'rgb(0, 0, 0)'))).toBe(true);
  await expect(push.locator('.pushDisplay')).toHaveCSS('background-color', 'rgb(16, 20, 22)');
  await page.screenshot({path: testInfo.outputPath('push-show.png'), fullPage: true});
  await page.locator('.experiencePanel').getByRole('button', {name: 'Stop', exact: true}).click();
});
