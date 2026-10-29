import {test, expect} from '@playwright/test';
import {desktopBridge, emitSurface} from './desktopTestHarness';
import {compileVisualFrame} from '../src/surfaceModel';
import type {SurfaceView} from '../src/types';

test('desktop switches layouts during Show without restarting or enabling actions', async ({page}) => {
  const view: SurfaceView = {selected_state: null, frame: 0, sessions: [], available_actions: [],
    overflow_count: 0, activity_motion: false, control_revision: 1};
  const prefs: Record<string, unknown> = {};
  const commands: string[] = [];
  const experience = (playing: boolean) => ({protocol: 1, type: 'experience_state', status: playing ? 'playing' : 'idle',
    kind: playing ? 'show' : null, title: playing ? 'A light' : null, detail: playing ? 'Prelude' : null,
    caption: playing ? 'A light' : null, cue_index: 0, elapsed_ms: 1000, duration_ms: 50000,
    tempo: 1, audio_asset: null, audio_cue: null, audio_slot: null, audio_sequence: 0, start_delay_ms: 0, reason: null});
  const frame = {protocol: 1, type: 'performance_frame', grid: Array.from({length: 8}, () => Array(8).fill('#ff00aa')),
    top: Array(8).fill('#000000'), right: Array(8).fill('#000000')};
  await desktopBridge(page, async (method, params) => {
    if (method === 'settings') return Object.assign(prefs, params);
    if (method === 'status') return {version: '0.2.0', settings: prefs, inputs: [], outputs: [], profiles: [], midi: null, lan_host: '127.0.0.1'};
    if (method === 'inspect_codex') return {available: true, version: '0.165.0', tested_version: '0.165.0'};
    if (method === 'list_conversations') return {available: true, conversations: []};
    if (method === 'paired_devices') return {devices: []};
    if (method === 'snapshot') return {messages: [{protocol: 1, type: 'authenticated', admin: true, lan_enabled: false},
      {protocol: 1, type: 'surface', visual_protocol: 1, view, visual_frame: compileVisualFrame(view)}, experience(false)]};
    if (method === 'surface') {
      commands.push(String(params.type));
      if (params.type === 'start_experience') {await emitSurface(page, experience(true)); await emitSurface(page, frame);}
      if (params.type === 'stop_experience') await emitSurface(page, experience(false));
      return {};
    }
    throw Error(`Unexpected request: ${method}`);
  });
  await page.goto('/');
  const switcher = page.getByRole('group', {name: 'Surface layout'});
  await switcher.getByRole('button', {name: 'Stream Deck', exact: true}).click();
  await page.getByRole('button', {name: 'Demo & Show', exact: true}).click();
  await page.getByRole('menuitem', {name: 'Show', exact: true}).click();
  const deck = page.getByLabel('Stream Deck-style control surface');
  await expect(deck.locator('.deckShowKey')).toHaveCount(15);
  await expect(deck.locator('.deckShowKey').first()).toHaveCSS('background-color', 'rgb(255, 0, 170)');
  await expect(deck.locator('button')).toHaveCount(0);
  await page.screenshot({path: test.info().outputPath('stream-deck-show.png')});
  const nextFrame = {...frame, grid: Array.from({length: 8}, () => Array(8).fill('#00bb44'))};
  await emitSurface(page, nextFrame);
  await expect(deck.locator('.deckShowKey').first()).toHaveCSS('background-color', 'rgb(0, 187, 68)');
  const before = [...commands];
  await switcher.getByRole('button', {name: 'Stream Deck XL', exact: true}).click();
  await expect(deck.locator('.deckShowKey')).toHaveCount(32);
  await expect(deck.locator('.deckShowKey').first()).toHaveCSS('background-color', 'rgb(0, 187, 68)');
  await switcher.getByRole('button', {name: 'Stream Deck Neo', exact: true}).click();
  await expect(deck.locator('.deckShowKey')).toHaveCount(8);
  await expect(deck.locator('button')).toHaveCount(0);
  await switcher.getByRole('button', {name: 'Grid', exact: true}).click();
  await expect(page.locator('.performanceSurface .matrixPad').first()).toHaveCSS('background-color', 'rgb(0, 187, 68)');
  await switcher.getByRole('button', {name: 'Stream Deck', exact: true}).click();
  expect(commands).toEqual(before);
  await page.getByRole('button', {name: 'Back to live pad'}).click();
  await expect(deck.locator('.deckSessionKey')).toHaveCount(8);
  await expect(deck.locator('.deckShowKey')).toHaveCount(0);
  await expect.poll(() => prefs.surface_layout).toBe('stream-deck');
  expect(commands.filter(command => command === 'start_experience')).toHaveLength(1);
});
