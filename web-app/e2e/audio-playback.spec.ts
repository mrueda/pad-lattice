import {expect, test, type Page, type WebSocketRoute} from '@playwright/test';

async function observeAudio(page: Page) {
  await page.addInitScript(() => {
    const tracked = window as unknown as {__players: HTMLAudioElement[]};
    tracked.__players = [];
    window.Audio = new Proxy(window.Audio, {
      construct(target, args) {
        const player = Reflect.construct(target, args) as HTMLAudioElement;
        tracked.__players.push(player);
        return player;
      },
    });
  });
}

async function playing(page: Page) {
  return page.evaluate(() => (window as unknown as {__players: HTMLAudioElement[]})
    .__players.filter((player) => !player.paused && !player.ended).length);
}

test('public Show stops its actual media player, including during startup', async ({page}) => {
  await observeAudio(page);
  await page.goto('/');
  await page.getByRole('button', {name: 'Show', exact: true}).click();
  await page.getByRole('button', {name: 'Sound off', exact: true}).click();
  await page.getByRole('button', {name: 'Start Show', exact: true}).click();
  await expect.poll(() => playing(page)).toBeGreaterThan(0);
  await page.locator('.experiencePanel').getByRole('button', {name: 'Stop', exact: true}).click();
  await expect.poll(() => playing(page)).toBe(0);
  await page.waitForTimeout(800);
  expect(await playing(page)).toBe(0);

  await page.getByRole('button', {name: 'Start Show', exact: true}).click();
  await page.locator('.experiencePanel').getByRole('button', {name: 'Stop', exact: true}).click();
  await page.waitForTimeout(800);
  expect(await playing(page)).toBe(0);
  await page.getByRole('button', {name: 'Start Show', exact: true}).click();
  await expect.poll(() => playing(page)).toBeGreaterThan(0);
  await page.getByRole('button', {name: 'Sandbox', exact: true}).click();
  await expect.poll(() => playing(page)).toBe(0);
});

test('an idle Show update stops audio on a paired surface', async ({page}) => {
  await observeAudio(page);
  let current: WebSocketRoute;
  await page.routeWebSocket('**/ws', (route) => {
    current = route;
    route.onMessage(data => {
      if (JSON.parse(String(data)).type === 'authenticate') route.send(JSON.stringify({
        protocol: 1, type: 'authenticated', admin: false, lan_enabled: true,
      }));
    });
  });
  await page.goto('http://127.0.0.1:4174/');
  await expect(page.getByText('Pad connected', {exact: true})).toBeVisible();
  await page.getByRole('button', {name: 'Sound', exact: true}).click();
  // Wait for the browser's silent user-gesture unlock to finish.
  await expect.poll(() => playing(page)).toBe(0);
  const experience = {protocol: 1, type: 'experience_state', kind: 'show',
    title: 'Audio regression', cue_index: 0, caption: null, detail: null,
    elapsed_ms: 0, duration_ms: 60000, tempo: 1,
    audio_asset: 'experiences/audio/constellation-v1.wav', audio_cue: null,
    audio_slot: null, audio_sequence: 0, start_delay_ms: 0, reason: null};
  current!.send(JSON.stringify({...experience, status: 'playing'}));
  await expect.poll(() => playing(page)).toBeGreaterThan(0);
  current!.send(JSON.stringify({...experience, status: 'idle'}));
  await expect.poll(() => playing(page)).toBe(0);
});
