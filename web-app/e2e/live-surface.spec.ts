import {expect, test} from '@playwright/test';

test.use({baseURL: 'http://127.0.0.1:4174'});

test.afterEach(async ({page}) => {
  const stop = page.locator('.experiencePanel').getByRole('button', {name: 'Stop'});
  if (await stop.isVisible().catch(() => false)) await stop.click();
});

test('receives live state, sends an action, and exposes local pairing', async ({page}, testInfo) => {
  await page.goto('/#admin=pad-lattice-e2e-admin');
  await expect(page.getByText('LIVE CODEX')).toBeVisible();
  await expect(page.getByText('Connected to Codex')).toBeVisible();
  await expect(page.getByRole('button', {name: /Reviewer Scene/})).toBeVisible();
  await expect(page.getByAltText('One-time device pairing QR code')).toBeVisible();

  if (testInfo.project.name === 'desktop') {
    await expect(page.getByText('Waiting for approval')).toBeVisible();
    await expect(page.getByRole('button', {name: 'Approve'})).toHaveCSS(
      'background-color',
      'rgb(85, 199, 106)',
    );
    await page.getByRole('button', {name: 'Approve'}).click();
    await expect(page.getByText('Success')).toBeVisible();
  } else {
    await expect(
      page.getByLabel('Pad-Lattice virtual control surface')
        .getByRole('button', {name: 'Select Reviewer'}),
    ).toHaveCSS('background-color', 'rgb(0, 174, 187)');
  }
});

test('local admin starts and stops the shared full-surface Show', async ({page}) => {
  await page.goto('/#admin=pad-lattice-e2e-admin');
  await expect(page.getByText('Connected to Codex')).toBeVisible();

  await page.getByRole('button', {name: 'Show'}).click();
  await expect(page.getByText('PLAYING')).toBeVisible();
  await expect(page.getByText('PERFORMANCE')).toBeVisible();
  await expect(page.locator('.matrixPad').first()).toHaveCSS(
    'background-color',
    /rgb\(/,
  );

  await page.locator('.experiencePanel').getByRole('button', {name: 'Stop'}).click();
  await expect(page.getByText('READY')).toBeVisible();
  await expect(page.getByText('SELECTED AGENT')).toBeVisible();
});

test('live Demo accepts the same scene and action controls', async ({page}) => {
  await page.goto('/#admin=pad-lattice-e2e-admin');
  await page.getByRole('button', {name: 'Demo'}).click();

  await expect(page.getByText('The Reviewer needs you.')).toBeVisible();
  await page.getByRole('button', {name: 'Select Reviewer'}).first().click();
  await expect(page.getByText('Approve the review.')).toBeVisible();
  await page.getByRole('button', {name: 'Approve'}).click();
  await expect(page.getByText('The Tests need attention.')).toBeVisible();
});
