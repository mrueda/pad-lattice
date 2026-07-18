import {expect, test} from '@playwright/test';

test.use({baseURL: 'http://127.0.0.1:4174'});

test('receives live state, sends an action, and exposes local pairing', async ({page}, testInfo) => {
  await page.goto('/');
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
