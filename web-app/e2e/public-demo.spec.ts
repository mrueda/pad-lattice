import {expect, test} from '@playwright/test';

test('autoplays selection, approval, and rejection without asking for clicks', async ({page}) => {
  await page.clock.install();
  await page.clock.pauseAt(new Date(Date.now() + 1000));
  await page.goto('/');
  await expect(page.locator('.modeSwitch').getByRole('button', {name: 'Demo'})).toHaveClass(/active/);
  await expect(page.getByRole('heading', {name: 'Reviewer needs permission.'})).toBeVisible();
  await expect(page.locator('.matrixPad')).toHaveCount(64);
  await expect(page.locator('.sceneControl')).toHaveCount(8);
  await expect(page.locator('.railControl')).toHaveCount(8);
  await expect(page.getByLabel('Demo playback')).toContainText('AUTOPLAY DEMO');
  await expect(page.getByLabel('Next action')).toHaveCount(0);
  await expect(page.locator('.railControl:enabled, .sceneControl:enabled')).toHaveCount(0);
  await expect(page.locator('.sceneControl.guidedControl')).toHaveAttribute(
    'aria-label',
    'Select Reviewer',
  );
  await expect(page.locator('.sessionRow.guidedRow')).toContainText('Reviewer');

  await page.clock.runFor(6800);
  await expect(page.locator('.sceneControl .demoPointer.pressed')).toBeVisible();
  await page.clock.runFor(200);
  await expect(page.getByRole('heading', {name: 'Allow the test command?'})).toBeVisible();
  await expect(page.locator('.demoNarrative')).toContainText('npm test outside the sandbox');
  await expect(page.locator('.railControl.guidedControl')).toHaveAttribute('aria-label', 'Approve');
  await page.clock.runFor(7000);
  await expect(page.getByRole('heading', {name: 'Now Tests needs a decision.'})).toBeVisible();
  await expect(page.locator('.selectedReadout')).toContainText('Reviewer');
  await page.clock.runFor(7000);
  await expect(page.getByRole('heading', {name: 'Decline the installation.'})).toBeVisible();
  await expect(page.locator('.railControl.guidedControl')).toHaveAttribute('aria-label', 'Reject');
  await page.clock.runFor(7000);
  await expect(page.getByRole('heading', {name: 'Two decisions. The right agents.'})).toBeVisible();
  await page.clock.runFor(7000);
  await expect(page.getByRole('button', {name: 'Pause demo', exact: true})).toBeDisabled();
  await page.getByRole('button', {name: 'Try it yourself', exact: true}).click();
  await expect(page.getByLabel('Scenario', {exact: true})).toHaveValue('parallel');
  await expect(page.getByText('Browser simulation. No hardware or Codex connection required.', {exact: true})).toBeVisible();
  await expect(page.getByText('SIMULATED AGENTS', {exact: true})).toBeVisible();
});

test('pauses, resumes, replays, and stops advancing outside the Demo tab', async ({page}) => {
  await page.clock.install();
  await page.clock.pauseAt(new Date(Date.now() + 1000));
  await page.goto('/');
  await page.getByLabel('Demo playback').waitFor();
  await page.clock.runFor(5000);
  await page.getByRole('button', {name: 'Pause demo', exact: true}).click();
  const position = await page.getByLabel('Demo progress').getAttribute('value');
  await page.clock.runFor(20000);
  await expect(page.getByLabel('Demo progress')).toHaveAttribute('value', position!);
  await page.getByRole('button', {name: 'Resume demo', exact: true}).click();
  await page.clock.runFor(2000);
  await expect(page.getByRole('heading', {name: 'Allow the test command?'})).toBeVisible();
  await page.getByRole('button', {name: 'Sandbox', exact: true}).click();
  await page.clock.runFor(20000);
  await page.getByRole('button', {name: 'Demo', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'Allow the test command?'})).toBeVisible();
  await page.getByRole('button', {name: 'Replay demo', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'Reviewer needs permission.'})).toBeVisible();
  await expect(page.getByLabel('Demo progress')).toHaveAttribute('value', '0');
  await expect(page.locator('.demoPointer')).toHaveCount(0);
});

test('keeps the current Show story beat beside the lights', async ({page}) => {
  await page.goto('/');
  await page.locator('.modeSwitch').getByRole('button', {name: 'Show'}).click();
  await expect(page.locator('.sceneControl')).toHaveText(Array(8).fill(''));
  await expect(page.locator('.sessionRow')).toHaveCount(0);
  await expect(page.getByRole('button', {name: /^Select /})).toHaveCount(0);
  await expect(page.locator('.surfaceFooter')).toContainText('FULL SURFACE');
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
  await expect(page.locator('.sceneControl')).toHaveText(Array(8).fill(''));
  await expect(page.locator('.sessionRow')).toHaveCount(0);
  await expect(page.locator('.surfaceFooter')).not.toContainText('Reviewer');
  await page.screenshot({path: test.info().outputPath('show-stopped.png'), fullPage: true});
});

test('sandbox targets one session and records actions without claiming immediate success', async ({page}) => {
  await page.goto('/');
  await page.getByRole('button', {name: 'Sandbox'}).click();

  await expect(page.getByLabel('Scenario', {exact: true})).toHaveValue('parallel');
  await page.getByRole('button', {name: 'View Reviewer', exact: true}).click();
  await expect(page.getByLabel('View agent')).toContainText('GRID: Reviewer');
  await expect(page.getByRole('button', {name: 'View Reviewer', exact: true})).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', {name: 'Approve'}).click();
  await expect(page.getByLabel('Reviewer state')).toHaveValue('running');
  await expect(page.getByLabel('Builder state')).toHaveValue('running');
  await expect(page.getByLabel('Tests state')).toHaveValue('error');
  await expect(page.getByRole('button', {name: 'Approve', exact: true})).toBeDisabled();
  await expect(page.locator('.playgroundHistory summary')).toContainText('Reviewer: approve received; work resumed.');

  await page.getByRole('button', {name: 'Stop'}).click();
  await expect(page.getByLabel('Reviewer state')).toHaveValue('cancelled');
  await page.getByRole('button', {name: 'Restart scenario'}).click();
  await expect(page.getByLabel('Reviewer state')).toHaveValue('waiting_for_approval');
  await expect(page.locator('.selectedReadout')).toContainText('Builder');
});

test('answered requests and disconnected targets lose approval controls', async ({page}) => {
  const sockets: string[] = [];
  page.on('websocket', (socket) => sockets.push(socket.url()));
  await page.goto('/');
  await page.getByRole('button', {name: 'Sandbox', exact: true}).click();
  await page.getByLabel('Scenario', {exact: true}).selectOption('resolved');
  await expect(page.getByRole('button', {name: 'Approve', exact: true})).toBeEnabled();
  await page.getByRole('button', {name: 'Reviewer permission answered in Codex'}).click();
  await expect(page.getByRole('button', {name: 'Approve', exact: true})).toBeDisabled();
  await expect(page.getByRole('button', {name: 'Stop', exact: true})).toBeEnabled();

  await page.getByLabel('Scenario', {exact: true}).selectOption('disconnect');
  await page.getByRole('button', {name: 'Reviewer disconnects'}).click();
  await expect(page.locator('.selectedReadout')).toContainText('No session selected');
  await expect(page.locator('.sceneControl').nth(1)).toBeDisabled();
  await expect(page.locator('.railControl:enabled')).toHaveCount(0);
  await page.getByRole('button', {name: 'Builder requests permission'}).click();
  await expect(page.locator('.railControl:enabled')).toHaveCount(0);
  await page.getByRole('button', {name: 'Select Builder', exact: true}).first().click();
  await expect(page.getByRole('button', {name: 'Approve', exact: true})).toBeEnabled();
  // Vite's development hot-reload socket is not an agent connection.
  expect(sockets.filter((url) => !url.includes('token='))).toEqual([]);
});

test('eight-session vocabulary is editable and Show cannot dispatch hidden actions', async ({page}) => {
  await page.goto('/');
  await page.getByRole('button', {name: 'Sandbox', exact: true}).click();
  await page.getByLabel('Scenario', {exact: true}).selectOption('vocabulary');
  await expect(page.locator('.sessionRow')).toHaveCount(8);
  await page.getByLabel('Agent 8 state').selectOption('waiting_for_approval');
  await page.getByRole('button', {name: 'Select Agent 8', exact: true}).first().click();
  await expect(page.locator('.sceneControl').nth(7)).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', {name: 'Reject', exact: true}).click();
  await expect(page.getByLabel('Agent 8 state')).toHaveValue('cancelled');
  await page.getByRole('button', {name: 'Demo', exact: true}).click();
  await page.getByRole('button', {name: 'Pause demo', exact: true}).click();
  await page.getByRole('button', {name: 'Show', exact: true}).click();
  await expect(page.locator('.railControl:enabled')).toHaveCount(0);
  await expect(page.locator('.sceneControl:enabled')).toHaveCount(0);
  await page.getByRole('button', {name: 'Demo', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'Reviewer needs permission.'})).toBeVisible();
});

test('keeps the controller within the viewport width and equally sized across tabs', async ({page}) => {
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
  const demoWidth = metrics.surface!.right - metrics.surface!.left;
  for (const mode of ['Sandbox', 'Show']) {
    await page.locator('.modeSwitch').getByRole('button', {name: mode, exact: true}).click();
    const width = await page.locator('.virtualSurface').evaluate(surface => surface.getBoundingClientRect().width);
    expect(width).toBeCloseTo(demoWidth, 0);
  }
});

test('remembers the browser theme without changing the visual protocol colors', async ({page}) => {
  await page.goto('/');
  const colors = () => page.locator('.matrixPad').evaluateAll(pads => pads.map(pad => getComputedStyle(pad).backgroundColor));
  await expect(page.locator('.matrixPad')).toHaveCount(64);
  const before = await colors();
  await page.getByRole('button', {name: 'Switch to light theme', exact: true}).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  expect(await colors()).toEqual(before);
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await page.getByRole('button', {name: 'Switch to dark theme', exact: true}).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
});

test('theme switching works when browser storage is blocked', async ({page}) => {
  await page.addInitScript(() => {
    for (const method of ['getItem', 'setItem']) Object.defineProperty(Storage.prototype, method, {
      value: () => { throw new DOMException('Storage blocked', 'SecurityError'); },
    });
  });
  await page.goto('/');
  await page.getByRole('button', {name: 'Switch to light theme', exact: true}).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await expect(page.getByLabel('Demo playback')).toBeVisible();
});
