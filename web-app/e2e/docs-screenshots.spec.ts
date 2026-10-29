import {test, expect} from '@playwright/test';
import {fileURLToPath} from 'node:url';
import {desktopBridge, emitSurface} from './desktopTestHarness';
import {compileVisualFrame} from '../src/surfaceModel';
import type {SurfaceView} from '../src/types';

// Opt-in publishing keeps ordinary test runs from rewriting documentation assets.
test('capture current desktop layouts with simulated conversations', async ({page}, info) => {
  test.skip(process.env.UPDATE_DOCS_SCREENSHOTS !== '1' || info.project.name !== 'desktop');
  await page.setViewportSize({width: 1440, height: 1120});
  let view: SurfaceView = {selected_state: 'waiting_for_approval', frame: 0, control_revision: 1,
    sessions: [
      {slot: 0, label: 'Implementation', state: 'running', accent: 'cyan', selected: false},
      {slot: 1, label: 'Review', state: 'waiting_for_approval', accent: 'magenta', selected: true},
      {slot: 2, label: 'Tests', state: 'idle', accent: 'lime', selected: false},
      {slot: 5, label: 'Documentation', state: 'waiting_for_reply', accent: 'teal', selected: false},
    ], available_actions: ['approve', 'reject'], overflow_count: 0, activity_motion: false};
  const preferences: Record<string, unknown> = {light_theme: true};
  const surface = () => ({protocol: 1, type: 'surface', visual_protocol: 1, view, visual_frame: compileVisualFrame(view)});
  await desktopBridge(page, async (method, params) => {
    if (method === 'settings') return Object.assign(preferences, params);
    if (method === 'status') return {version: '0.2.0', settings: preferences, inputs: [], outputs: [], profiles: [], midi: null, lan_host: '127.0.0.1'};
    if (method === 'inspect_codex') return {available: true, version: '0.165.0', tested_version: '0.165.0'};
    if (method === 'paired_devices') return {devices: []};
    if (method === 'snapshot') return {messages: [{protocol: 1, type: 'authenticated', admin: true, lan_enabled: false}, surface()]};
    if (method === 'list_conversations') return {available: true, conversations: view.sessions.map(s => ({
      id: `example-${s.slot}`, name: s.label, cwd: '/projects/example', state: s.state === 'waiting_for_approval' ? 'approval' : s.state === 'waiting_for_reply' ? 'waiting' : s.state,
      connected: true, managed: true, slot: s.slot, accent: s.accent}))};
    if (method === 'attention') return {revision: view.control_revision, overflow_count: 0,
      sessions: view.sessions.filter(s => s.state.startsWith('waiting')).map(s => ({...s, age_seconds: 45, pending_count: 1, child_attention_count: 0}))};
    if (method === 'approval_status') return {slot: 1, revision: view.control_revision, pending_count: 1,
      approval: {kind: 'command', command: 'npm test', reason: 'Run the project tests before continuing.', cwd: '/projects/example', truncated: false, additional_permissions: false}};
    if (method === 'surface') {
      if (params.type === 'select_session') {
        view = {...view, sessions: view.sessions.map(s => ({...s, selected: s.slot === params.slot}))};
        await emitSurface(page, surface());
      }
      return {};
    }
    throw Error(`Unexpected documentation capture request: ${method}`);
  });
  await page.goto('/');
  await expect(page.getByRole('region', {name: 'Approval request'})).toContainText('npm test');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  const picker = page.getByRole('button', {name: /Codex conversations/});
  if (await picker.getAttribute('aria-expanded') === 'true') await picker.click();
  const layouts = page.getByRole('group', {name: 'Surface layout'});
  for (const [label, filename] of [['Grid', 'desktop-grid'], ['Stream Deck', 'desktop-stream-deck'], ['Stream Deck Neo', 'desktop-stream-deck-neo']]) {
    await layouts.getByRole('button', {name: label, exact: true}).click();
    await expect(layouts.getByRole('button', {name: label, exact: true})).toHaveAttribute('aria-pressed', 'true');
    const bounds = await page.locator(label === 'Grid' ? '.virtualSurface' : '.streamDeckSurface').boundingBox();
    expect(bounds).not.toBeNull();
    expect(bounds!.x).toBeGreaterThanOrEqual(0);
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(1440);
    expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(1120);
    await page.screenshot({path: fileURLToPath(new URL(`../../docs-site/static/img/${filename}.png`, import.meta.url))});
  }
});
