import {test, expect} from '@playwright/test';
import {compileVisualFrame} from '../src/surfaceModel';
import type {SurfaceView} from '../src/types';

test('desktop discovers then explicitly connects and disconnects without launching', async ({page}) => {
  const methods: string[] = [];
  const preferences: Record<string, unknown> = {};
  let unavailable = false;
  let connected = false;
  const surfaceMessage = () => {
    const view: SurfaceView = {selected_state: connected ? 'running' : null, frame: 0,
      sessions: connected ? [{slot: 0, state: 'running', selected: true, accent: 'cyan', label: 'Review implementation'}] : [],
      available_actions: [], overflow_count: 0, activity_motion: false};
    return {protocol: 1, type: 'surface', visual_protocol: 1, view, visual_frame: compileVisualFrame(view)};
  };
  await page.exposeFunction('__discoveryTestRequest', async (method: string, params: Record<string, unknown>) => {
    methods.push(method);
    if (method === 'list_conversations') return unavailable
      ? {available: false, conversations: [], error: 'Codex disconnected'}
      : {available: true, conversations: [
        {id: 'session-review', name: 'Review implementation', cwd: '/projects/implementation', state: 'approval', connected, managed: connected, slot: connected ? 0 : null},
        {id: 'session-tests', name: 'A long conversation name that must not overlap status or controls', cwd: '/projects/a-very-long-folder-name/with/several/subfolders', state: 'running'},
      ]};
    if (method === 'attach_conversation' || method === 'detach_conversation') {
      expect(params.thread_id).toBe('session-review');
      connected = method === 'attach_conversation';
      await page.evaluate(message => {
        (window as unknown as {__emitSurface: (message: unknown) => void}).__emitSurface(message);
      }, surfaceMessage());
      return {slot: 0};
    }
    if (method === 'surface') return {};
    if (method === 'settings') return Object.assign(preferences, params);
    if (method === 'status') return {settings: preferences, inputs: [], outputs: [], profiles: [], midi: null, lan_host: '127.0.0.1'};
    if (method === 'inspect_codex') return {available: true, version: '0.164.0', tested: true};
    if (method === 'snapshot') return {messages: [{protocol: 1, type: 'authenticated', admin: true, lan_enabled: false}, surfaceMessage()]};
    throw Error(`Unexpected desktop method: ${method}`);
  });
  await page.addInitScript(() => {
    let id = 0;
    const callbacks = new Map<number, (event: unknown) => void>();
    const listeners = new Map<number, string>();
    Object.assign(window, {__emitSurface: (payload: unknown) => {
      for (const [handler, event] of listeners) if (event === 'pad-lattice-surface') callbacks.get(handler)?.({payload});
    }});
    Object.assign(window, {__TAURI_INTERNALS__: {
      transformCallback: (callback: (event: unknown) => void) => { callbacks.set(++id, callback); return id; },
      unregisterCallback: (handler: number) => callbacks.delete(handler),
      invoke: async (command: string, args: {method: string; params: object; handler: number; event: string; eventId: number}) => {
        if (command === 'plugin:event|listen') { listeners.set(args.handler, args.event); return args.handler; }
        if (command === 'plugin:event|unlisten') { listeners.delete(args.eventId); return; }
        if (command !== 'desktop_request') throw Error(`Unexpected native command: ${command}`);
        return (window as unknown as {__discoveryTestRequest: (method: string, params: object) => unknown}).__discoveryTestRequest(args.method, args.params);
      },
    }});
  });
  await page.goto('/');
  const list = page.getByRole('region', {name: 'Open Codex conversations'});
  await expect(list.getByText('Review implementation', {exact: true})).toBeVisible();
  await expect(list.getByText('Approval needed', {exact: true})).toBeVisible();
  await expect(list.getByText('Not connected', {exact: true})).toHaveCount(2);
  expect(methods).not.toContain('attach_conversation');
  const explore = page.getByRole('button', {name: 'Explore', exact: true});
  await expect(page.getByRole('tab')).toHaveCount(0);
  await expect(explore).toBeEnabled();
  await explore.click();
  await page.getByRole('menuitem', {name: 'Demo', exact: true}).click();
  await expect(page.getByText('SIMULATION', {exact: true})).toBeVisible();
  await page.getByRole('button', {name: 'Back to live pad', exact: true}).click();
  await expect(page.getByText('CODEX CLI', {exact: true})).toBeVisible();
  await explore.press('ArrowDown');
  await page.getByRole('menuitem', {name: 'Demo', exact: true}).press('End');
  await expect(page.getByRole('menuitem', {name: 'Show', exact: true})).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.getByText('SIMULATION', {exact: true})).toBeVisible();
  await page.getByRole('button', {name: 'Connect Review implementation', exact: true}).click();
  await expect(list.getByText('Connected, Scene 1', {exact: true})).toBeVisible();
  await expect(explore).toBeDisabled();
  await expect(page.getByText('CODEX CLI', {exact: true})).toBeVisible();
  await expect(page.getByRole('button', {name: 'Back to live pad', exact: true})).toHaveCount(0);
  await page.getByRole('button', {name: 'Maximize pad', exact: true}).click();
  await expect(list).not.toBeVisible();
  await expect(page.locator('.surfaceFooter')).toContainText('Review implementation');
  await expect(page.locator('.appHeader')).not.toBeVisible();
  await expect(page.locator('.appFooter')).not.toBeVisible();
  await expect(page.locator('.contextPane')).not.toBeVisible();
  await expect(page.getByRole('button', {name: 'Reload interface', exact: true})).toHaveCount(0);
  const padBounds = await page.locator('.virtualSurface').boundingBox();
  expect(padBounds).not.toBeNull();
  expect(padBounds!.y + padBounds!.height).toBeLessThanOrEqual(page.viewportSize()!.height);
  if (page.viewportSize()!.width > page.viewportSize()!.height) {
    expect(padBounds!.height).toBeGreaterThan(page.viewportSize()!.height * 0.9);
  }
  await page.screenshot({path: test.info().outputPath('maximized-pad.png'), fullPage: true});
  await page.keyboard.press('Escape');
  await expect(list).toBeVisible();
  await page.getByRole('button', {name: 'Maximize pad', exact: true}).click();
  await page.getByRole('button', {name: 'Restore workspace', exact: true}).click();
  await expect.poll(() => preferences.pad_focused).toBe(false);
  await expect(list).toBeVisible();
  expect(await page.evaluate(() => document.dispatchEvent(new MouseEvent('contextmenu', {bubbles: true, cancelable: true})))).toBe(false);
  await expect(page.getByRole('button', {name: 'Reload interface', exact: true})).toHaveCount(0);
  await page.getByRole('button', {name: 'Settings', exact: true}).click();
  await expect(page.getByRole('button', {name: 'Save', exact: true})).toHaveCount(0);
  await page.getByRole('button', {name: 'Reload interface', exact: true}).click();
  await expect(list.getByText('Connected, Scene 1', {exact: true})).toBeVisible();
  await expect(explore).toBeDisabled();
  await expect(page.getByLabel('Codex working folder', {exact: false}).first()).not.toBeVisible();
  await page.screenshot({path: test.info().outputPath('desktop-discovery.png'), fullPage: true});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole('button', {name: 'Disconnect Review implementation', exact: true}).click();
  await expect(list.getByText('Not connected', {exact: true})).toHaveCount(2);
  await expect(explore).toBeEnabled();
  unavailable = true;
  await page.getByRole('button', {name: 'Refresh chats', exact: true}).click();
  await expect(list.getByText('Codex disconnected', {exact: true})).toBeVisible();
  await expect(list.getByText('Review implementation', {exact: true})).toHaveCount(0);
  expect(methods).not.toContain('launch_session');
  expect(methods.filter(method => method === 'attach_conversation')).toHaveLength(1);
});
