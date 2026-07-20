import {expect, test} from '@playwright/test';

test('teaches selection, approval, retry, and multi-agent success', async ({page}) => {
  await page.goto('/');
  await expect(page.locator('.modeSwitch').getByRole('button', {name: 'Demo'})).toHaveClass(/active/);
  await expect(page.getByRole('heading', {name: 'The Reviewer needs you.'})).toBeVisible();
  await expect(page.locator('.matrixPad')).toHaveCount(64);
  await expect(page.locator('.sceneControl')).toHaveCount(8);
  await expect(page.locator('.railControl')).toHaveCount(8);
  await expect(page.getByLabel('Next action')).toContainText('Select Reviewer - Scene 2');
  await expect(page.locator('.sceneControl.guidedControl')).toHaveAttribute(
    'aria-label',
    'Select Reviewer',
  );
  await expect(page.locator('.sessionRow.guidedRow')).toContainText('Reviewer');

  await page.getByRole('button', {name: 'Select Reviewer'}).first().click();
  await expect(page.getByRole('heading', {name: 'Approve the review.'})).toBeVisible();
  await expect(page.getByLabel('Next action')).toContainText('Approve Reviewer');
  await expect(page.locator('.railControl.guidedControl')).toHaveAttribute('aria-label', 'Approve');
  await page.getByRole('button', {name: 'Approve'}).click();

  await expect(page.getByLabel('Next action')).toContainText('Select Tests - Scene 3');
  await page.getByRole('button', {name: 'Select Tests'}).first().click();
  await expect(page.getByRole('heading', {name: 'Retry the test agent.'})).toBeVisible();
  await expect(page.getByLabel('Next action')).toContainText('Retry Tests');
  await page.getByRole('button', {name: 'Retry'}).click();

  await expect(page.getByRole('heading', {name: 'The agents form a constellation.'})).toBeVisible();
  await expect(page.getByLabel('Next action')).toHaveCount(0);
  await expect(page.getByRole('button', {name: 'Sandbox'})).toBeEnabled();
});

test('keeps the current Show story beat beside the lights', async ({page}) => {
  await page.goto('/');
  await page.locator('.modeSwitch').getByRole('button', {name: 'Show'}).click();
  await expect(page.locator('.experiencePanel').getByRole('button', {name: 'Start Demo'})).toHaveCount(0);
  await page.locator('.experiencePanel').getByRole('button', {name: 'Start Show'}).click();

  await expect(page.locator('.performanceStory')).toBeVisible();
  await expect(page.locator('.performanceStory')).toContainText('Alone');
  await expect(page.locator('.showNarrative h1')).toHaveText('Alone');
  const metrics = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
    scrollX: window.scrollX,
  }));
  expect(metrics.scroll).toBeLessThanOrEqual(metrics.viewport);
  expect(metrics.scrollX).toBe(0);

  await page.locator('.experiencePanel').getByRole('button', {name: 'Stop'}).click();
});

test('opens the sandbox directly and exercises state-driven actions', async ({page}) => {
  await page.goto('/');
  await page.getByRole('button', {name: 'Sandbox'}).click();

  await expect(page.getByRole('heading', {name: 'Every scene is yours.'})).toBeVisible();
  const agentOneState = page.getByLabel('Agent 1 state');
  await expect(agentOneState).toBeVisible();
  await agentOneState.selectOption('waiting_for_approval');
  await page.getByRole('button', {name: 'Approve'}).click();
  await expect(agentOneState).toHaveValue('success');

  await page.getByRole('button', {name: 'Select Agent 2'}).first().click();
  await page.getByRole('button', {name: 'Stop'}).click();
  await expect(page.getByLabel('Agent 2 state')).toHaveValue('cancelled');
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
