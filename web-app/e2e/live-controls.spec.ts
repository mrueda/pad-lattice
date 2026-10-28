import {expect, test, type Page, type WebSocketRoute} from '@playwright/test';
import {compileVisualFrame} from '../src/surfaceModel';
import type {SurfaceView} from '../src/types';

const initialView = (): SurfaceView => ({
  control_revision: 20, selected_state: 'running', frame: 0,
  sessions: [
    {slot: 0, label: 'Builder', accent: 'cyan', state: 'running', selected: true},
    {slot: 1, label: 'Reviewer', accent: 'magenta', state: 'waiting_for_approval', selected: false},
    {slot: 2, label: 'Tests', accent: 'lime', state: 'error', selected: false},
  ],
  available_actions: ['stop'], activity_motion: false, overflow_count: 0,
});
const surface = (view: SurfaceView) => ({protocol: 1, type: 'surface', visual_protocol: 1, view,
  visual_frame: compileVisualFrame(view)});

async function nativeBridge(page: Page) {
  await page.addInitScript(() => {
    let id = 0;
    const callbacks = new Map<number, (event: unknown) => void>();
    const listeners = new Map<number, string>();
    Object.assign(window, {__emitSurface: (payload: unknown) => {
      for (const [handler, event] of listeners) if (event === 'pad-lattice-surface') callbacks.get(handler)?.({payload});
    }, __TAURI_INTERNALS__: {
      transformCallback: (callback: (event: unknown) => void) => {callbacks.set(++id, callback); return id;},
      unregisterCallback: (handler: number) => callbacks.delete(handler),
      invoke: async (command: string, args: {method: string; params: object; handler: number; event: string; eventId: number}) => {
        if (command === 'plugin:event|listen') {listeners.set(args.handler, args.event); return args.handler;}
        if (command === 'plugin:event|unlisten') {listeners.delete(args.eventId); return;}
        if (command !== 'desktop_request') throw Error(`Unexpected native command: ${command}`);
        return (window as unknown as {__multiSessionRequest: (method: string, params: object) => unknown})
          .__multiSessionRequest(args.method, args.params);
      },
    }});
  });
}

for (const desktop of [false, true]) {
  test(`${desktop ? 'Desktop' : 'browser'} targets the displayed revision and keeps multi-session identity clear`, async ({page}) => {
    let view = initialView();
    const inputs: Record<string, unknown>[] = [];
    let socket: WebSocketRoute;
    const emit = async () => {
      if (desktop) await page.evaluate(message => {
        (window as unknown as {__emitSurface: (payload: unknown) => void}).__emitSurface(message);
      }, surface(view));
      else socket!.send(JSON.stringify(surface(view)));
    };
    const authenticated = {protocol: 1, type: 'authenticated', admin: desktop, session_token: null, lan_enabled: false};
    if (desktop) {
      await page.exposeFunction('__multiSessionRequest', (method: string, params: Record<string, unknown>) => {
        if (method === 'snapshot') return {messages: [authenticated, surface(view)]};
        if (method === 'surface') {inputs.push(params); return {};}
        if (method === 'settings') return {};
        if (method === 'paired_devices') return {devices: []};
        if (method === 'status') return {version: '0.2.0', settings: {}, inputs: [], outputs: [], profiles: [], midi: null, lan_host: '127.0.0.1'};
        if (method === 'inspect_codex') return {available: true, version: 'test', tested: true};
        if (method === 'list_conversations') return {available: true, conversations: view.sessions.map(s => ({
          id: `session-${s.label}`, name: s.label, cwd: `/projects/${s.label.toLowerCase()}`, slot: s.slot,
          accent: s.accent, state: s.state === 'waiting_for_approval' ? 'approval' : s.state,
          connected: true, launcher: true,
        }))};
        throw Error(`Unexpected method: ${method}`);
      });
      await nativeBridge(page);
    } else {
      await page.route('**/config.json', route => route.fulfill({json: {mode: 'live', protocol: 1}}));
      await page.routeWebSocket('**/ws', route => {
        socket = route;
        route.onMessage(data => {
          const message = JSON.parse(String(data));
          if (message.type === 'authenticate') {
            route.send(JSON.stringify(authenticated));
            route.send(JSON.stringify(surface(view)));
          } else inputs.push(message);
        });
      });
    }
    await page.goto('/');
    const pad = page.getByLabel('Pad-Lattice virtual control surface');
    await expect(pad.getByRole('button', {name: 'Select Builder', exact: true})).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('.sessionRow .attentionState')).toHaveCount(2);
    await pad.getByRole('button', {name: 'Select Reviewer', exact: true}).click();
    await expect.poll(() => inputs.at(-1)).toEqual({protocol: 1, type: 'select_session', slot: 1, expected_revision: 20});

    view = {...view, control_revision: 21, selected_state: 'waiting_for_approval', available_actions: ['approve', 'reject'],
      sessions: view.sessions.map(s => ({...s, selected: s.slot === 1}))};
    await emit();
    await expect(pad.getByRole('button', {name: 'Select Reviewer', exact: true})).toHaveAttribute('aria-pressed', 'true');
    if (desktop) {
      const selected = page.getByRole('region', {name: 'Selected Codex conversation'});
      await expect(selected).toContainText('Scene 2');
      await expect(selected.getByRole('heading')).toHaveText('Reviewer');
      await selected.getByRole('button', {name: 'Approve', exact: true}).click();
    } else await pad.getByRole('button', {name: 'Approve', exact: true}).click();
    await expect.poll(() => inputs.at(-1)).toEqual({protocol: 1, type: 'action', action: 'approve', expected_revision: 21});

    view = {...view, control_revision: 22, sessions: view.sessions.map(s => s.slot === 2 ? {...s, state: 'waiting_for_reply'} : s)};
    await emit();
    await expect(page.locator('.sessionRow .waiting_for_reply')).toBeVisible();
    await expect(pad.getByRole('button', {name: 'Select Reviewer', exact: true})).toHaveAttribute('aria-pressed', 'true');
    expect(await page.locator('.sessionRow strong').allTextContents()).toEqual(['Builder', 'Reviewer', 'Tests']);
    await pad.getByRole('button', {name: 'Reject', exact: true}).click();
    await expect.poll(() => inputs.at(-1)).toEqual({protocol: 1, type: 'action', action: 'reject', expected_revision: 22});
    await page.screenshot({path: test.info().outputPath(desktop ? 'desktop-multi-session.png' : 'browser-multi-session.png'), fullPage: true});

    view = {...view, control_revision: null};
    await emit();
    await expect(pad.getByRole('button', {name: 'Approve', exact: true})).toBeDisabled();
    await expect(page.locator('.sessionRow > button:enabled')).toHaveCount(0);
    if (desktop) await expect(page.getByRole('region', {name: 'Selected Codex conversation'})
      .getByRole('button', {name: 'Approve', exact: true})).toBeDisabled();
    expect(inputs).toHaveLength(3);

    view = {...view, control_revision: 23, selected_state: null, available_actions: [],
      sessions: view.sessions.filter(s => s.slot !== 1).map(s => ({...s, selected: false}))};
    await emit();
    await expect(pad.getByRole('button', {name: 'Approve', exact: true})).toBeDisabled();
    await expect(page.locator('.sceneControl[aria-pressed="true"]')).toHaveCount(0);
    if (desktop) await expect(page.getByRole('heading', {name: 'No conversation selected', exact: true})).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}
