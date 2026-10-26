import {expect, test, type WebSocketRoute} from '@playwright/test';
import {compileVisualFrame} from '../src/surfaceModel';
import type {SurfaceView} from '../src/types';

test.use({baseURL: 'http://127.0.0.1:4174'});

test.afterEach(async ({page}) => {
  const stop = page.locator('.experiencePanel').getByRole('button', {name: 'Stop'});
  if (await stop.isVisible().catch(() => false)) await stop.click();
});

test('receives live state, sends an action, and exposes local pairing', async ({page}, testInfo) => {
  await page.goto('/#admin=pad-lattice-e2e-admin');
  await expect(page.getByText('CODEX CLI', {exact: true})).toBeVisible();
  await expect(page.getByText('Pad connected')).toBeVisible();
  await expect(page.getByRole('button', {name: /Reviewer Scene/})).toBeVisible();
  await expect(page.getByText('OR PAIR MANUALLY', {exact: true})).toBeVisible();
  await expect(page.getByAltText('Scan to pair automatically without entering a PIN')).toBeVisible();
  await expect(page.getByRole('button', {name: 'Sound', exact: true})).toHaveCount(1);
  await expect(page.locator('.experiencePanel').getByRole('button', {name: /Sound/})).toHaveCount(0);

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
  await page.goto('http://127.0.0.1:4175/#admin=pad-lattice-e2e-admin');
  await expect(page.getByText('Pad connected')).toBeVisible();

  await page.getByRole('button', {name: 'Start Show'}).click();
  await expect(page.getByText('PLAYING')).toBeVisible();
  await expect(page.getByText('PERFORMANCE')).toBeVisible();
  await expect(page.locator('.performanceStory strong')).not.toBeEmpty();
  await expect(page.locator('.matrixPad').first()).toHaveCSS(
    'background-color',
    /rgb\(/,
  );

  await page.locator('.experiencePanel').getByRole('button', {name: 'Stop'}).click();
  await expect(page.getByText('READY')).toBeVisible();
  await expect(page.getByText('SELECTED AGENT')).toBeVisible();
});

test('live Demo accepts the same scene and action controls', async ({page}) => {
  await page.goto('http://127.0.0.1:4175/#admin=pad-lattice-e2e-admin');
  await page.getByRole('button', {name: 'Start Demo'}).click();

  await expect(page.getByText('The Reviewer needs you.')).toBeVisible();
  await page.getByRole('button', {name: 'Select Reviewer'}).first().click();
  await expect(page.getByText('Approve the review.')).toBeVisible();
  await page.getByRole('button', {name: 'Approve'}).click();
  await expect(page.getByText('The Tests need attention.')).toBeVisible();
});

test('a disconnected phone waits for manual reconnect and revocation asks for a new PIN', async ({page}) => {
  let connections = 0;
  let current: WebSocketRoute;
  await page.routeWebSocket('**/ws', route => {
    current = route;
    connections++;
    route.onMessage(data => {
      if (JSON.parse(String(data)).type === 'authenticate') route.send(JSON.stringify({
        protocol: 1, type: 'authenticated', admin: false, session_token: 'paired-token', lan_enabled: true,
      }));
    });
  });
  await page.goto('/#pair=one-use-token');
  await expect(page.getByText('Pad connected', {exact: true})).toBeVisible();
  current!.send(JSON.stringify({protocol: 1, type: 'device_disconnected'}));
  current!.close({code: 1000});
  await expect(page.getByRole('button', {name: 'Reconnect', exact: true})).toBeVisible();
  await page.waitForTimeout(1500);
  expect(connections).toBe(1);
  await page.getByRole('button', {name: 'Reconnect', exact: true}).click();
  await expect(page.getByText('Pad connected', {exact: true})).toBeVisible();
  expect(connections).toBe(2);
  await page.getByRole('button', {name: 'Disconnect this device', exact: true}).click();
  await expect(page.getByText('Disconnected on this device.', {exact: true}).first()).toBeVisible();
  await expect(page.getByRole('button', {name: 'Reconnect', exact: true})).toBeVisible();
  await page.waitForTimeout(1500);
  expect(connections).toBe(2);
  await page.getByRole('button', {name: 'Reconnect', exact: true}).click();
  await expect(page.getByText('Pad connected', {exact: true})).toBeVisible();
  expect(connections).toBe(3);
  current!.send(JSON.stringify({protocol: 1, type: 'error', code: 'forbidden', error: 'Device access revoked'}));
  current!.close({code: 1008});
  await expect(page.getByLabel('Pairing PIN', {exact: true})).toBeVisible();
  await page.waitForTimeout(1500);
  expect(connections).toBe(3);
});

test('connection loss clears stale controls and waits for manual reconnect', async ({page}) => {
  let current: WebSocketRoute;
  let connections = 0;
  let available = true;
  const view: SurfaceView = {selected_state: 'waiting_for_approval', frame: 0,
    sessions: [{slot: 0, state: 'waiting_for_approval', selected: true, accent: 'cyan', label: 'Recovery test'}],
    available_actions: ['approve', 'reject'], overflow_count: 0, activity_motion: false};
  await page.routeWebSocket('**/ws', route => {
    current = route;
    connections++;
    route.onMessage(data => {
      if (JSON.parse(String(data)).type === 'authenticate') {
        if (!available) {route.close({code: 1011}); return;}
        route.send(JSON.stringify({protocol: 1, type: 'authenticated', admin: false, lan_enabled: true}));
        route.send(JSON.stringify({protocol: 1, type: 'surface', view, visual_protocol: 1, visual_frame: compileVisualFrame(view)}));
      }
    });
  });
  await page.goto('/');
  await expect(page.getByRole('button', {name: 'Approve', exact: true})).toBeEnabled();
  current!.close({code: 1011});
  await expect(page.getByText('Desktop disconnected.', {exact: true}).first()).toBeVisible();
  await expect(page.getByRole('button', {name: 'Approve', exact: true})).toBeDisabled();
  await page.waitForTimeout(2600);
  expect(connections).toBe(1);
  available = false;
  await page.getByRole('button', {name: 'Reconnect', exact: true}).click();
  await expect(page.getByText('Cannot reach Pad-Lattice.', {exact: true}).first()).toBeVisible();
  await page.waitForTimeout(2600);
  expect(connections).toBe(2);
  available = true;
  await page.getByRole('button', {name: 'Reconnect', exact: true}).click();
  await expect.poll(() => connections).toBe(3);
  await expect(page.getByRole('button', {name: 'Approve', exact: true})).toBeEnabled();
  await expect(page.locator('.connectionRecovery')).toHaveCount(0);
});

test('paired phones show shared playback without Demo and Show controls', async ({page}) => {
  let current: WebSocketRoute;
  await page.routeWebSocket('**/ws', route => {
    current = route;
    route.onMessage(data => {
      if (JSON.parse(String(data)).type === 'authenticate') route.send(JSON.stringify({
        protocol: 1, type: 'authenticated', admin: false, lan_enabled: true,
      }));
    });
  });
  await page.goto('/');
  await expect(page.getByText('Pad connected', {exact: true})).toBeVisible();
  await expect(page.locator('.experiencePanel')).toHaveCount(0);
  await expect(page.getByRole('button', {name: 'Sound', exact: true})).toBeVisible();
  await expect(page.getByRole('button', {name: 'Disconnect this device', exact: true})).toBeVisible();
  current!.send(JSON.stringify({protocol: 1, type: 'experience_state', status: 'playing', kind: 'show',
    title: 'Shared Show', cue_index: 0, caption: 'A shared constellation', detail: 'Opening',
    elapsed_ms: 0, duration_ms: 10000, tempo: 1, audio_asset: null, audio_cue: null,
    audio_slot: null, audio_sequence: 0, start_delay_ms: 0, reason: null}));
  current!.send(JSON.stringify({protocol: 1, type: 'performance_frame',
    grid: Array.from({length: 8}, () => Array(8).fill('#00ff00')),
    top: Array(8).fill('#00ff00'), right: Array(8).fill('#00ff00')}));
  await expect(page.locator('.performanceStory strong')).toHaveText('A shared constellation');
  await expect(page.locator('.experiencePanel')).toHaveCount(0);
  await expect(page.getByRole('button', {name: 'Start Show', exact: true})).toHaveCount(0);
  await expect(page.locator('.matrixPad').first()).toHaveCSS('background-color', 'rgb(0, 255, 0)');
});
