import {expect, test} from '@playwright/test';
import {desktopBridge, emitSurface} from './desktopTestHarness';
import {compileVisualFrame} from '../src/surfaceModel';
import {accentNames, type SurfaceView} from '../src/types';

test('Neo indicates attention on the other page without changing the action target', async ({page}) => {
  let view: SurfaceView = {selected_state: 'running', control_revision: 10, frame: 0,
    sessions: accentNames.map((accent, slot) => ({slot, accent, label: `Agent ${slot + 1}`, selected: slot === 0,
      state: slot === 1 ? 'waiting_for_reply' : slot === 5 ? 'waiting_for_approval' : slot === 6 ? 'error' : 'running'})),
    available_actions: ['stop'], overflow_count: 0, activity_motion: false};
  const commands: Record<string, unknown>[] = [];
  const message = () => ({protocol: 1, type: 'surface', visual_protocol: 1, view, visual_frame: compileVisualFrame(view)});
  await desktopBridge(page, async (method, params) => {
    if (method === 'settings') return {surface_layout: 'stream-deck-neo', ...params};
    if (method === 'status') return {version: '0.2.0', settings: {}, inputs: [], outputs: [], profiles: [], midi: null, lan_host: '127.0.0.1'};
    if (method === 'inspect_codex') return {available: true, version: '0.165.0', tested_version: '0.165.0'};
    if (method === 'paired_devices') return {devices: []};
    if (method === 'list_conversations') return {available: true, conversations: []};
    if (method === 'attention') return {revision: view.control_revision, sessions: [], overflow_count: 0};
    if (method === 'snapshot') return {messages: [{protocol: 1, type: 'authenticated', admin: true, lan_enabled: false}, message()]};
    if (method === 'surface') {commands.push(params); return {};}
    throw Error(`Unexpected request: ${method}`);
  });
  await page.goto('/');
  const deck = page.getByLabel('Stream Deck-style control surface');
  const next = deck.getByRole('button', {name: 'Next page, page 2: 2 conversations need attention', exact: true});
  await expect(next.locator('.deckPageAttention')).toHaveText('2');
  await expect(deck.getByRole('status')).toHaveText('Page 2: 2 conversations need attention');
  await expect(deck.getByRole('button', {name: 'Select Agent 1', exact: true})).toHaveAttribute('aria-pressed', 'true');
  view = {...view, control_revision: null};
  await emitSurface(page, message());
  await expect(deck.locator('.deckPageAttention')).toHaveCount(0);
  view = {...view, control_revision: 10};
  await emitSurface(page, message());
  await expect(next.locator('.deckPageAttention')).toHaveText('2');
  await next.click();
  const previous = deck.getByRole('button', {name: 'Previous page, page 1: 1 conversation needs attention', exact: true});
  await expect(previous.locator('.deckPageAttention')).toHaveText('1');
  await expect(deck.getByRole('button', {name: 'Stop', exact: true})).toContainText('Agent 1');
  expect(commands).toEqual([]);

  view = {...view, control_revision: 11,
    sessions: view.sessions.map(session => ({...session, state: session.slot === 1 ? 'running' : session.state}))};
  await emitSurface(page, message());
  await expect(deck.getByRole('button', {name: 'Previous page', exact: true})).toBeVisible();
  await expect(deck.locator('.deckPageAttention')).toHaveCount(0);
  await deck.getByRole('button', {name: 'Previous page', exact: true}).click();
  await expect(deck.getByRole('button', {name: 'Next page, page 2: 2 conversations need attention', exact: true})).toBeVisible();
  view = {...view, control_revision: 12, sessions: view.sessions.map(session => ({...session, state: 'idle'}))};
  await emitSurface(page, message());
  await expect(deck.getByRole('button', {name: 'Next page', exact: true})).toBeVisible();
  await expect(deck.locator('.deckPageAttention')).toHaveCount(0);
  await expect(deck.getByRole('button', {name: 'Select Agent 1', exact: true})).toHaveAttribute('aria-pressed', 'true');
  expect(commands).toEqual([]);
});
