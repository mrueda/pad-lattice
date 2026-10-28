import {test, expect} from '@playwright/test';
import {desktopBridge, emitSurface} from './desktopTestHarness';
import {readFileSync} from 'node:fs';
import {compileVisualFrame} from '../src/surfaceModel';
import type {DemoManifest, SurfaceView} from '../src/types';

test('desktop demo has one mode chooser and highlights each requested control', async ({page}) => {
  const manifest = JSON.parse(readFileSync(new URL('../public/experiences/demo-v1.json', import.meta.url), 'utf8')) as DemoManifest;
  let index = -1;
  const view = (): SurfaceView => {
    const sessions = index < 0 ? [] : manifest.stages[index].view.sessions;
    return {sessions, selected_state: sessions.find(s => s.selected)?.state ?? null,
      available_actions: index < 0 ? [] : manifest.stages[index].view.available_actions,
      control_revision: index + 2, frame: 0, overflow_count: 0, activity_motion: false};
  };
  const surface = () => ({protocol: 1, type: 'surface', visual_protocol: 1, view: view(), visual_frame: compileVisualFrame(view())});
  const emit = async () => {
    await emitSurface(page, {protocol: 1, type: 'experience_state', status: index < 0 ? 'idle' : 'playing',
      kind: index < 0 ? null : 'demo', title: manifest.title, cue_index: index < 0 ? null : index,
      caption: index < 0 ? null : manifest.stages[index].prompt.title,
      detail: index < 0 ? null : manifest.stages[index].prompt.detail,
      elapsed_ms: 0, duration_ms: null, tempo: 1, audio_asset: null, audio_cue: null,
      audio_slot: null, audio_sequence: 0, start_delay_ms: 0, reason: null});
    await emitSurface(page, surface());
  };
  await desktopBridge(page, async (method, params) => {
    if (method === 'settings') return {};
    if (method === 'status') return {version: '0.2.0', settings: {}, inputs: [], outputs: [], profiles: [], midi: null, lan_host: '127.0.0.1'};
    if (method === 'inspect_codex') return {available: true, version: '0.165.0', tested_version: '0.165.0'};
    if (method === 'list_conversations') return {available: true, conversations: []};
    if (method === 'paired_devices') return {devices: []};
    if (method === 'snapshot') return {messages: [{protocol: 1, type: 'authenticated', admin: true, lan_enabled: false}, surface()]};
    if (method === 'surface') {
      if (params.type === 'start_experience') index = 0;
      else if (params.type === 'stop_experience') index = -1;
      else if (params.type === 'select_session') {expect(params.slot).toBe(1); index = 1;}
      else if (params.type === 'action') {expect(params.action).toBe('approve'); index = 3;}
      await emit(); return {};
    }
    throw Error(`Unexpected method: ${method}`);
  });
  await page.goto('/');
  await page.getByRole('button', {name: 'Demo & Show', exact: true}).click();
  await page.getByRole('menuitem', {name: 'Demo', exact: true}).click();
  await expect(page.getByRole('button', {name: 'Demo & Show', exact: true})).toHaveText('Demo');
  await expect(page.getByText('INTERACTIVE DEMO', {exact: true})).toBeVisible();
  await expect(page.getByRole('button', {name: 'Start Show'})).toHaveCount(0);
  await expect(page.getByRole('button', {name: 'Start Demo'})).toHaveCount(0);
  await expect(page.locator('.liveDemoCue')).toContainText('Select Reviewer');
  const reviewer = page.locator('.sceneRail').getByRole('button', {name: 'Select Reviewer'});
  await expect(reviewer).toHaveClass(/guidedControl/);
  await page.emulateMedia({reducedMotion: 'reduce'});
  await expect(reviewer).toHaveCSS('animation-name', 'none');
  const cueBounds = await page.locator('.liveDemoCue').boundingBox();
  const padBounds = await page.locator('.virtualSurface').boundingBox();
  expect(cueBounds!.y + cueBounds!.height).toBeLessThanOrEqual(padBounds!.y);
  await expect(page.getByRole('region', {name: 'Open Codex conversations'})).toBeHidden();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({path: test.info().outputPath('demo-select.png'), fullPage: true});
  await reviewer.click();
  await expect(page.locator('.liveDemoCue')).toContainText('Approve Reviewer');
  await expect(page.locator('.topRail').getByRole('button', {name: 'Approve', exact: true})).toHaveClass(/guidedControl/);
  await expect(page.locator('.topRail').getByRole('button', {name: 'Stop', exact: true}).locator('svg')).toBeVisible();
  await page.screenshot({path: test.info().outputPath('demo-approve.png'), fullPage: true});
  await page.locator('.topRail').getByRole('button', {name: 'Approve', exact: true}).click();
  await expect(page.locator('.liveDemoCue')).toContainText('Select Tests');
  await page.getByRole('button', {name: 'Back to live pad', exact: true}).click();
  await expect(page.locator('.liveDemoCue')).toHaveCount(0);
  await expect(page.getByText('INTERACTIVE DEMO', {exact: true})).toHaveCount(0);
});
