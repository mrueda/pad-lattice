import {readFile} from 'node:fs/promises';
import {test, expect, type Page} from '@playwright/test';

type FixtureWindow = Window & {connectElgatoStreamDeckSocket: (...args: string[]) => void;
  deckHost: {messages: Array<{event: string; payload: Record<string, unknown>}>; receive: (payload: unknown) => void}};

async function inspector(page: Page, action = 'session') {
  await page.route('**/stream-deck-inspector/**', async route => {
    const filename = new URL(route.request().url()).pathname.split('/').pop();
    if (!['settings.html', 'settings.css', 'settings.js'].includes(filename ?? '')) return route.abort();
    const body = await readFile(new URL(`../../integrations/stream-deck/io.github.mrueda.pad-lattice.sdPlugin/ui/${filename}`, import.meta.url));
    await route.fulfill({body, contentType: filename?.endsWith('.html') ? 'text/html' : filename?.endsWith('.css') ? 'text/css' : 'text/javascript'});
  });
  await page.addInitScript(() => {
    const messages: Array<{event: string; payload: Record<string, unknown>}> = [];
    class HostSocket {
      static OPEN = 1;
      readyState = 1;
      onopen?: () => void;
      onmessage?: (event: {data: string}) => void;
      constructor() {
        (window as unknown as FixtureWindow).deckHost = {messages,
          receive: payload => this.onmessage?.({data: JSON.stringify({event: 'sendToPropertyInspector', payload})})};
        queueMicrotask(() => this.onopen?.());
      }
      send(data: string) { messages.push(JSON.parse(data)); }
    }
    Object.defineProperty(window, 'WebSocket', {value: HostSocket});
  });
  await page.goto('/stream-deck-inspector/settings.html');
  await page.evaluate(action => {
    (window as unknown as FixtureWindow).connectElgatoStreamDeckSocket('12345', 'key-context', 'registerPropertyInspector', '{}',
      JSON.stringify({action: `io.github.mrueda.pad-lattice.${action}`, payload: {settings: {slot: 3}}}));
  }, action);
}

async function status(page: Page, connection: string, error = '') {
  await page.evaluate(({connection, error}) => (window as unknown as FixtureWindow).deckHost.receive({connection, error,
    status: connection === 'connected' ? 'Connected' : connection === 'connecting' ? 'Connecting' : 'Pair device',
    address: 'http://127.0.0.1:8765'}), {connection, error});
}

test('Stream Deck setup pairs once, recovers from errors, and keeps credentials out of settings', async ({page}) => {
  await page.setViewportSize({width: 420, height: 600});
  await inspector(page);
  await status(page, 'unpaired');
  await expect(page.getByLabel('Session slot')).toHaveValue('3');
  await page.getByLabel('Session slot').selectOption({value: '6'});
  await expect(page.getByText('Shared by all Pad-Lattice keys')).toBeVisible();
  await page.getByLabel('Address', {exact: true}).fill('http://192.168.1.43:8001');
  await status(page, 'unpaired');
  await expect(page.getByLabel('Address', {exact: true})).toHaveValue('http://192.168.1.43:8001');
  await page.getByLabel('One-use PIN').fill('123456');
  await page.getByRole('button', {name: 'Pair', exact: true}).click();
  await expect(page.getByLabel('One-use PIN')).toHaveValue('');
  await expect(page.getByRole('button', {name: 'Pair', exact: true})).toBeDisabled();
  await expect(page.getByRole('button', {name: 'Cancel', exact: true})).toBeVisible();
  await status(page, 'unpaired', 'PIN expired or rejected. Create a new code in Pad-Lattice.');
  await expect(page.getByRole('alert')).toContainText('PIN expired or rejected');
  await expect(page.getByRole('button', {name: 'Pair', exact: true})).toBeEnabled();
  await page.screenshot({path: test.info().outputPath('stream-deck-setup-error.png')});
  await page.getByLabel('One-use PIN').fill('654321');
  await page.getByRole('button', {name: 'Pair', exact: true}).click();
  await status(page, 'connected');
  await expect(page.getByRole('status')).toHaveText('Connected');
  await expect(page.getByLabel('One-use PIN')).toBeHidden();
  await expect(page.getByRole('alert')).toBeHidden();
  await page.screenshot({path: test.info().outputPath('stream-deck-setup-connected.png')});
  await page.getByRole('button', {name: 'Disconnect', exact: true}).click();
  const messages = await page.evaluate(() => (window as unknown as FixtureWindow).deckHost.messages);
  expect(messages.filter(m => m.event === 'setSettings')).toEqual([{event: 'setSettings', context: 'key-context', payload: {slot: 6}}]);
  expect(messages.some(m => m.payload?.type === 'pair' && m.payload.address === 'http://192.168.1.43:8001' && m.payload.pin === '123456')).toBe(true);
  expect(messages.some(m => m.payload?.type === 'disconnect')).toBe(true);
  expect(messages.some(m => m.event === 'setGlobalSettings')).toBe(false);
});

test('action keys show the shared connection without a session selector', async ({page}) => {
  await inspector(page, 'approve');
  await status(page, 'connected');
  await expect(page.getByLabel('Session slot')).toBeHidden();
  await expect(page.getByRole('status')).toHaveText('Connected');
  await expect(page.getByRole('button', {name: 'Disconnect', exact: true})).toBeVisible();
  await expect(page.getByLabel('One-use PIN')).toBeHidden();
});
