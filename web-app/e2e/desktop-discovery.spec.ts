import {test, expect} from '@playwright/test';
import {compileVisualFrame} from '../src/surfaceModel';
import type {SurfaceView} from '../src/types';
import {desktopBridge} from './desktopTestHarness';

test('picker stays open when connecting several chats and respects manual collapse', async ({page}) => {
  const connected = new Map<string, number>();
  const view: SurfaceView = {selected_state: null, frame: 0, control_revision: 1,
    sessions: [], available_actions: [], overflow_count: 0, activity_motion: false};
  await desktopBridge(page, (method, params) => {
    if (method === 'settings' || method === 'surface') return {};
    if (method === 'status') return {version: '0.2.0', settings: {}, inputs: [], outputs: [], profiles: [], midi: null, lan_host: '127.0.0.1'};
    if (method === 'inspect_codex') return {available: true, version: '0.165.0', tested_version: '0.165.0'};
    if (method === 'paired_devices') return {devices: []};
    if (method === 'snapshot') return {messages: [{protocol: 1, type: 'authenticated', admin: true, lan_enabled: false},
      {protocol: 1, type: 'surface', visual_protocol: 1, view, visual_frame: compileVisualFrame(view)}]};
    if (method === 'list_conversations') return {available: true, conversations: ['Builder', 'Reviewer'].map(name => ({
      id: name, name, cwd: '/project', state: 'running', connected: connected.has(name), managed: connected.has(name),
      slot: connected.get(name) ?? null}))};
    if (method === 'attach_conversation') {
      connected.set(String(params.thread_id), connected.size);
      return {slot: connected.get(String(params.thread_id))};
    }
    if (method === 'detach_conversation') {connected.delete(String(params.thread_id)); return {};}
    throw Error(`Unexpected request: ${method}`);
  });
  await page.goto('/');
  const picker = page.getByRole('button', {name: /Codex conversations/});
  await page.getByRole('button', {name: 'Connect Builder', exact: true}).click();
  await expect(page.getByRole('button', {name: 'Disconnect Builder', exact: true})).toBeVisible();
  await expect(picker).toHaveAttribute('aria-expanded', 'true');
  await page.getByRole('button', {name: 'Connect Reviewer', exact: true}).click();
  await expect(page.getByRole('button', {name: 'Disconnect Reviewer', exact: true})).toBeVisible();
  await expect(picker).toHaveAttribute('aria-expanded', 'true');
  await page.getByRole('button', {name: 'Refresh chats', exact: true}).click();
  await expect(picker).toHaveAttribute('aria-expanded', 'true');
  await picker.press('Escape');
  await expect(picker).toHaveAttribute('aria-expanded', 'false');
  await page.getByRole('button', {name: 'Refresh chats', exact: true}).click();
  await expect(picker).toHaveAttribute('aria-expanded', 'false');
  expect([...connected.keys()]).toEqual(['Builder', 'Reviewer']);
  await picker.click();
  await page.getByRole('button', {name: 'Remove Builder from Pad-Lattice', exact: true}).click();
  const dialog = page.getByRole('dialog', {name: 'Remove from Pad-Lattice?'});
  await expect(dialog).toContainText('Codex history is not deleted');
  await dialog.getByRole('button', {name: 'Cancel', exact: true}).click();
  expect(connected.has('Builder')).toBe(true);
  await page.getByRole('button', {name: 'Remove Builder from Pad-Lattice', exact: true}).click();
  await dialog.getByRole('button', {name: 'Remove', exact: true}).click();
  await expect(page.getByRole('button', {name: 'Disconnect Builder', exact: true})).toHaveCount(0);
  await page.getByRole('button', {name: 'Refresh chats', exact: true}).click();
  await expect(page.getByRole('button', {name: 'Connect Builder', exact: true})).toHaveCount(0);
  expect([...connected.keys()]).toEqual(['Reviewer']);
  await page.getByRole('button', {name: 'Restore removed conversations', exact: true}).click();
  await expect(page.getByRole('button', {name: 'Connect Builder', exact: true})).toBeVisible();
});

test('desktop discovers then explicitly connects and disconnects without launching', async ({page}) => {
  const methods: string[] = [];
  const preferences: Record<string, unknown> = {};
  let unavailable = false;
  let empty = false;
  let connected = false;
  let networkUrl: string | null = null;
  let failNetwork = true;
  let testedCodexVersion = '0.164.0';
  let devices = [{id: 'phone-123456', name: 'Android / Chrome', kind: 'browser', connected: true}];
  const surfaceMessage = () => {
    const view: SurfaceView = {selected_state: connected ? 'running' : null, frame: 0,
      sessions: connected ? [{slot: 0, state: 'running', selected: true, accent: 'cyan', label: 'Review implementation'}] : [],
      available_actions: [], overflow_count: 0, activity_motion: false};
    return {protocol: 1, type: 'surface', visual_protocol: 1, view, visual_frame: compileVisualFrame(view)};
  };
  await page.exposeFunction('__discoveryTestRequest', async (method: string, params: Record<string, unknown>) => {
    methods.push(method);
    if (method === 'attention') return {revision: 0, sessions: [], overflow_count: 0};
    if (method === 'list_conversations') return unavailable
      ? {available: false, conversations: [], error: 'Codex disconnected'}
      : {available: true, conversations: empty ? [] : [
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
    if (method === 'paired_devices') return {devices};
    if (method === 'disconnect_device') {
      expect(params.device_id).toBe('phone-123456');
      devices = devices.map(device => ({...device, connected: false}));
      return {devices};
    }
    if (method === 'revoke_device') {
      expect(params.device_id).toBe('phone-123456');
      devices = [];
      return {devices};
    }
    if (method === 'surface') {
      if (params.type === 'create_pairing') await page.evaluate(() => {
        (window as unknown as {__emitSurface: (message: unknown) => void}).__emitSurface({protocol: 1, type: 'pairing',
          pin: '123456', pairing_url: 'http://192.168.1.43:8001/#pair=test-secret',
          qr_data_uri: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="132" height="132"/%3E', expires_in: 300});
      });
      return {};
    }
    if (method === 'settings') return Object.assign(preferences, params);
    if (method === 'lan') {
      expect(params).toEqual({host: '10.211.55.4', advertise_host: '192.168.1.43', port: 8001});
      if (failNetwork) throw new Error('Pairing port is already in use');
      networkUrl = 'http://192.168.1.43:8001';
      return {settings: preferences, inputs: [], outputs: [], profiles: [], midi: null,
        lan_host: '10.211.55.4', network_url: networkUrl};
    }
    if (method === 'status') return {version: '0.1.0', settings: preferences, inputs: [], outputs: [], profiles: [], midi: null,
      lan_host: networkUrl ? '10.211.55.4' : '127.0.0.1', network_url: networkUrl};
    if (method === 'inspect_codex') return {available: true, version: '0.165.0', tested: testedCodexVersion === '0.165.0', tested_version: testedCodexVersion};
    if (method === 'snapshot') return {messages: [{protocol: 1, type: 'authenticated', admin: true, lan_enabled: false}, surfaceMessage()]};
    throw Error(`Unexpected desktop method: ${method}`);
  });
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {value: {
      writeText: async (text: string) => {Object.assign(window, {__copiedDiagnostics: text});},
    }});
    Object.assign(window, {__audioPlays: 0});
    HTMLMediaElement.prototype.play = function () {
      const target = window as unknown as {__audioPlays: number};
      target.__audioPlays += 1;
      return Promise.resolve();
    };
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
  const list = page.getByRole('region', {name: 'Codex conversations'});
  await expect(list.getByText('Review implementation', {exact: true})).toBeVisible();
  await expect(list.getByText('Approval needed', {exact: true})).toBeVisible();
  await expect(list.getByText('Not connected', {exact: true})).toHaveCount(2);
  expect(methods).not.toContain('attach_conversation');
  await expect(page.getByText('No chats connected', {exact: true})).toBeVisible();
  await expect(page.getByText('Codex CLI 0.165.0', {exact: true})).toBeVisible();
  await expect(page.getByText(/Integration tested with/)).not.toBeVisible();
  await expect(page.getByRole('button', {name: '1 device connected', exact: true})).toHaveClass(/online/);
  await expect(page.getByRole('button', {name: 'MIDI: not connected', exact: true})).not.toHaveClass(/online/);
  await page.getByRole('button', {name: '1 device connected', exact: true}).click();
  const backToPad = page.getByRole('button', {name: 'Back to pad', exact: true});
  await expect(backToPad).toBeFocused();
  await expect(page.getByRole('region', {name: 'Paired devices'}).getByText('Android / Chrome')).toBeVisible();
  await page.getByRole('tab', {name: 'About', exact: true}).click();
  await expect(page.getByRole('region', {name: 'About Pad-Lattice'})).toContainText('Version 0.1.0');
  await expect(page.getByRole('region', {name: 'About Pad-Lattice'})).toContainText('Third-party credits');
  await expect(page.getByRole('region', {name: 'About Pad-Lattice'})).toContainText('python-rtmidi / RtMidi');
  await expect(page.locator('.desktopAbout .desktopNotice').first()).toHaveCSS('font-size', '14px');
  await expect(page.locator('.thirdPartyCredits small').first()).toHaveCSS('font-size', '12px');
  await page.getByRole('button', {name: 'Copy diagnostics', exact: true}).click();
  await expect(page.getByText('Diagnostics copied', {exact: true})).toBeVisible();
  const diagnostics = await page.evaluate(() => (window as unknown as {__copiedDiagnostics: string}).__copiedDiagnostics);
  expect(JSON.parse(diagnostics).devices.connected).toBe(1);
  expect(diagnostics).not.toMatch(/projects|phone-123456|Android/);
  await page.getByRole('button', {name: 'Bundled dependency notices', exact: true}).click();
  await expect(page.locator('.desktopAbout pre').last()).toContainText('PAD-LATTICE THIRD-PARTY NOTICES');
  await page.getByText('Dependency notices', {exact: true}).click();
  await page.screenshot({path: test.info().outputPath('about.png'), fullPage: true});
  await page.locator('.desktopSetup').evaluate(element => { element.scrollTop = element.scrollHeight; });
  await expect(backToPad).toBeInViewport();
  await page.screenshot({path: test.info().outputPath('settings-scrolled.png'), fullPage: true});
  await page.getByRole('tab', {name: 'Appearance & sound', exact: true}).click();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', {name: '1 device connected', exact: true})).toBeFocused();
  await expect(page.getByRole('button', {name: 'Pair device', exact: true})).toBeEnabled();
  await expect(page.getByRole('button', {name: 'Pair device', exact: true}).locator('svg.lucide-qr-code')).toBeVisible();
  await expect(page.locator('.contextPane .pairingPanel')).toHaveCount(0);
  const explore = page.getByRole('button', {name: 'Demo & Show', exact: true});
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
  await expect(page.locator('.sessionSection')).toHaveCount(0);
  await expect(page.locator('.surfaceFooter')).toContainText('FULL SURFACE');
  await expect(list).toBeHidden();
  await page.getByRole('button', {name: 'Back to live pad', exact: true}).click();
  await expect(list).toBeVisible();
  await page.getByRole('button', {name: 'Connect Review implementation', exact: true}).click();
  const picker = list.getByRole('button', {name: /Codex conversations/});
  await expect(picker).toHaveAttribute('aria-expanded', 'true');
  await expect(list.getByText('On pad, Scene 1', {exact: true})).toBeVisible();
  const swatch = page.locator('.sessionRow > button i').first();
  await expect(swatch).toHaveCSS('width', '12px');
  await expect(swatch).toHaveCSS('height', '12px');
  await expect(swatch).toHaveCSS('box-shadow', 'none');
  await expect(page.locator('.selectedConversation h2 i')).toHaveCSS('border-radius', '2px');
  await expect(explore).toBeDisabled();
  await expect(page.getByText('1 chat on pad', {exact: true})).toBeVisible();
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
  const selectedScene = await page.locator('.sceneControl[aria-pressed="true"]').boundingBox();
  expect(selectedScene!.x + selectedScene!.width + 5).toBeLessThanOrEqual(padBounds!.x + padBounds!.width);
  const geometry = await page.locator('.surfaceBody').evaluate(body => {
    const grid = body.querySelector('.matrixGrid')!.getBoundingClientRect();
    const cells = [...body.querySelectorAll('.matrixPad')].map(el => el.getBoundingClientRect());
    const scenes = [...body.querySelectorAll('.sceneControl')].map(el => el.getBoundingClientRect());
    return scenes.map((scene, index) => ({
      widthDifference: Math.abs(scene.width - cells[index * 8].width),
      centerDifference: Math.abs((scene.top + scene.height / 2) - (cells[index * 8].top + cells[index * 8].height / 2)),
      bottomOverflow: scene.bottom - grid.bottom,
    }));
  });
  for (const item of geometry) {
    expect(item.widthDifference).toBeLessThan(1);
    expect(item.centerDifference).toBeLessThan(1);
    expect(item.bottomOverflow).toBeLessThanOrEqual(1);
  }
  const originalViewport = page.viewportSize()!;
  for (const viewport of [{width: 1180, height: 860}, {width: 760, height: 620}]) {
    await page.setViewportSize(viewport);
    const pad = await page.locator('.virtualSurface').boundingBox();
    const selected = await page.locator('.sceneControl[aria-pressed="true"]').boundingBox();
    expect(selected!.x + selected!.width + 5).toBeLessThanOrEqual(pad!.x + pad!.width);
    expect(pad!.x + pad!.width).toBeLessThanOrEqual(viewport.width);
    expect(pad!.y + pad!.height).toBeLessThanOrEqual(viewport.height);
  }
  await page.setViewportSize(originalViewport);
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
  await page.getByRole('tab', {name: 'Codex', exact: true}).click();
  await expect(page.getByText('Installed Codex 0.165.0. Integration tested with 0.164.0.')).toBeVisible();
  await page.getByRole('tab', {name: 'Appearance & sound', exact: true}).click();
  await expect(page.getByText(/Integration tested with/)).not.toBeVisible();
  await page.getByRole('button', {name: 'Light', exact: true}).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await expect.poll(() => preferences.light_theme).toBe(true);
  await page.screenshot({path: test.info().outputPath('settings-light.png'), fullPage: true});
  await expect(page.locator('.virtualSurface')).not.toBeVisible();
  await expect(list).not.toBeVisible();
  await backToPad.click();
  await expect(page.getByRole('button', {name: 'Settings', exact: true})).toBeFocused();
  await expect(page.locator('.virtualSurface')).toBeVisible();
  await expect(page.locator('.virtualSurface')).toHaveCSS('background-color', 'rgb(197, 208, 208)');
  await page.screenshot({path: test.info().outputPath('workspace-light.png'), fullPage: true});
  await expect(list.getByText('On pad, Scene 1', {exact: true})).toBeVisible();
  await page.getByRole('button', {name: 'Settings', exact: true}).click();
  const sound = page.getByRole('checkbox', {name: 'Enable sound'});
  await page.getByRole('tab', {name: 'Devices', exact: true}).click();
  await page.getByRole('tab', {name: 'Browsers', exact: true}).click();
  await page.getByRole('checkbox', {name: 'VM shared network'}).check();
  const enableNetwork = page.getByRole('button', {name: 'Enable network access', exact: true});
  await enableNetwork.click();
  await expect(page.getByRole('alert')).toContainText('Enter the VM IPv4 address.');
  await page.getByLabel('VM IPv4 address', {exact: true}).fill('10.211.55.4');
  await enableNetwork.click();
  await expect(page.getByRole('alert')).toContainText('Enter the Mac / host IPv4 address.');
  await page.getByLabel('Mac / host IPv4 address', {exact: true}).fill('192.168.1.43');
  await enableNetwork.click();
  await expect(page.getByRole('alert')).toContainText('Pairing port is already in use');
  failNetwork = false;
  await enableNetwork.click();
  const pairingDialog = page.getByRole('dialog', {name: 'Pair a device'});
  await expect(pairingDialog).toBeVisible();
  await expect(pairingDialog.getByText('http://192.168.1.43:8001', {exact: true})).toBeVisible();
  await expect(pairingDialog).toContainText('No PIN needed');
  await expect(pairingDialog).toContainText('123456');
  await page.screenshot({path: test.info().outputPath('pairing-dialog.png'), fullPage: true});
  await page.keyboard.press('Escape');
  await expect(pairingDialog).not.toBeVisible();
  await expect(page.getByText('Network access enabled', {exact: true})).toBeVisible();
  await page.locator('.networkSetup summary').click();
  await expect(page.getByRole('button', {name: 'Disable network access'}).locator('svg')).toBeVisible();
  await page.locator('.networkSetup summary').click();
  await expect(page.getByRole('region', {name: 'Paired devices'})).toContainText('Android / Chrome');
  await page.getByRole('button', {name: 'Disconnect Android / Chrome', exact: true}).click();
  await expect(page.getByRole('region', {name: 'Paired devices'})).toContainText('Offline');
  await expect(page.getByRole('button', {name: '0 devices connected', exact: true})).not.toHaveClass(/online/);
  await page.getByRole('button', {name: 'Revoke access for Android / Chrome'}).click();
  await expect(page.getByRole('button', {name: 'Revoke access', exact: true}).locator('svg')).toBeVisible();
  await expect(page.getByRole('button', {name: 'Cancel', exact: true}).locator('svg')).toBeVisible();
  await page.screenshot({path: test.info().outputPath('revoke-confirmation.png'), fullPage: true});
  await page.getByRole('button', {name: 'Revoke access', exact: true}).click();
  await expect(page.getByText('No browsers paired', {exact: true})).toBeVisible();
  await page.screenshot({path: test.info().outputPath('phone-settings.png'), fullPage: true});
  await page.getByRole('tab', {name: 'Appearance & sound'}).click();
  const soundBounds = await sound.boundingBox();
  expect(soundBounds?.width).toBe(18);
  expect(soundBounds?.height).toBe(18);
  await page.screenshot({path: test.info().outputPath('sound-settings.png'), fullPage: true});
  await expect(sound).not.toBeChecked();
  await sound.check();
  await expect.poll(() => preferences.audio_enabled).toBe(true);
  const emitCue = () => page.evaluate(() => {
    (window as unknown as {__emitSurface: (message: unknown) => void}).__emitSurface(
      {protocol: 1, type: 'audio_cue', cue: 'approval', slot: 0});
  });
  await emitCue();
  await expect.poll(() => page.evaluate(() => (window as unknown as {__audioPlays: number}).__audioPlays)).toBe(1);
  await page.getByRole('button', {name: 'Sound', exact: true}).click();
  await expect(sound).not.toBeChecked();
  await expect.poll(() => preferences.audio_enabled).toBe(false);
  await emitCue();
  await page.waitForTimeout(200);
  expect(await page.evaluate(() => (window as unknown as {__audioPlays: number}).__audioPlays)).toBe(1);
  await expect(page.getByRole('button', {name: 'Save', exact: true})).toHaveCount(0);
  testedCodexVersion = '0.165.0';
  await page.getByRole('button', {name: 'Reload interface', exact: true}).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await expect(picker).toHaveAttribute('aria-expanded', 'false');
  await picker.click();
  await expect(list.getByText('On pad, Scene 1', {exact: true})).toBeVisible();
  await expect(explore).toBeDisabled();
  await expect(page.getByLabel('Codex working folder', {exact: false}).first()).not.toBeVisible();
  await page.screenshot({path: test.info().outputPath('desktop-discovery.png'), fullPage: true});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole('button', {name: 'Disconnect Review implementation', exact: true}).click();
  await expect(list.getByText('Not connected', {exact: true})).toHaveCount(2);
  await expect(explore).toBeEnabled();
  await expect(page.getByText('No chats connected', {exact: true})).toBeVisible();
  empty = true;
  await page.getByRole('button', {name: 'Refresh chats', exact: true}).click();
  await expect(list.getByText('No available Codex conversations', {exact: true})).toBeVisible();
  unavailable = true;
  await page.getByRole('button', {name: 'Refresh chats', exact: true}).click();
  await expect(list.getByText('Codex disconnected', {exact: true})).toBeVisible();
  await expect(list.getByText('Review implementation', {exact: true})).toHaveCount(0);
  expect(methods).not.toContain('launch_session');
  expect(methods.filter(method => method === 'attach_conversation')).toHaveLength(1);
  await page.getByRole('button', {name: 'Codex settings', exact: true}).click();
  await expect(page.getByRole('tab', {name: 'Codex', exact: true})).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByText(/Integration tested with/)).not.toBeVisible();
  await page.getByRole('tab', {name: 'Appearance & sound', exact: true}).click();
  await page.getByRole('button', {name: 'Dark', exact: true}).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await expect.poll(() => preferences.light_theme).toBe(false);
  await page.screenshot({path: test.info().outputPath('settings-dark.png'), fullPage: true});
});
