import {test, expect} from '@playwright/test';
import {desktopBridge, emitSurface} from './desktopTestHarness';
import {compileVisualFrame, tokenColor} from '../src/surfaceModel';
import {accentNames, type SurfaceView} from '../src/types';

test('eight connected agents leave the pad visible and selection carries one consistent identity', async ({page}) => {
  let view: SurfaceView = {selected_state: 'waiting_for_approval', frame: 0, control_revision: 12,
    sessions: accentNames.map((accent, slot) => ({slot, accent, label: `Agent ${slot + 1}`,
      state: slot === 1 ? 'waiting_for_approval' : 'running', selected: slot === 1})),
    available_actions: ['approve', 'reject'], overflow_count: 0, activity_motion: false};
  const preferences = {};
  const message = () => ({protocol: 1, type: 'surface', visual_protocol: 1, view, visual_frame: compileVisualFrame(view)});
  const inputs: Record<string, unknown>[] = [];
  await desktopBridge(page, async (method, params) => {
    if (method === 'settings') return Object.assign(preferences, params);
    if (method === 'snapshot') return {messages: [{protocol: 1, type: 'authenticated', admin: true, lan_enabled: false}, message()]};
    if (method === 'status') return {version: '0.2.0', settings: preferences, inputs: [], outputs: [], profiles: [], midi: null, lan_host: '127.0.0.1'};
    if (method === 'inspect_codex') return {available: true, version: '0.165.0', tested_version: '0.165.0'};
    if (method === 'paired_devices') return {devices: []};
    if (method === 'attention') return {revision: view.control_revision,
      sessions: view.sessions.filter(s => s.state === 'waiting_for_approval').map(s => ({...s, age_seconds: 12})), overflow_count: 0};
    if (method === 'list_conversations') return {available: true, conversations: view.sessions.map(s => ({id: `session-${s.slot}`,
      name: s.label, cwd: '/projects/workspace', state: s.state, connected: true, managed: true, slot: s.slot, accent: s.accent}))};
    if (method === 'surface') {
      inputs.push(params);
      if (params.type === 'select_session') {
        view = {...view, control_revision: 13, selected_state: 'running', available_actions: ['stop'],
          sessions: view.sessions.map(s => ({...s, selected: s.slot === params.slot}))};
        await emitSurface(page, message());
      }
      return {};
    }
    throw Error(`Unexpected request: ${method}`);
  });
  await page.goto('/');
  const picker = page.getByRole('button', {name: /Codex conversations/});
  await expect(picker).toHaveAttribute('aria-expanded', 'false');
  await expect(page.locator('.openConversationList')).toBeHidden();
  await expect(page.locator('.connectionSummary')).toHaveCount(0);
  const selected = page.getByRole('region', {name: 'Selected Codex conversation'});
  const pad = page.getByLabel('Pad-Lattice virtual control surface');
  await expect(selected.getByRole('heading')).toHaveText('Agent 2');
  await expect(pad.locator('.surfaceFooter')).toContainText('SCENE 2');
  expect(await selected.evaluate(el => el.style.getPropertyValue('--session-accent'))).toBe(tokenColor('accent:magenta:selected'));
  expect(await pad.evaluate(el => el.style.getPropertyValue('--session-accent'))).toBe(tokenColor('accent:magenta:selected'));

  for (const viewport of [{width: 1440, height: 1000}, {width: 1280, height: 800}, {width: 1024, height: 768}, {width: 760, height: 620}]) {
    await page.setViewportSize(viewport);
    const bounds = await pad.boundingBox();
    expect(bounds!.height).toBeGreaterThan(viewport.height * .4);
    expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(viewport.height - 38);
    const grid = await pad.locator('.matrixGrid').boundingBox();
    expect(Math.abs(grid!.width - grid!.height)).toBeLessThan(1);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({path: test.info().outputPath(`workspace-${viewport.width}-dark.png`)});
  }

  const layout = page.getByRole('group', {name: 'Surface layout'});
  await layout.getByRole('button', {name: 'Stream Deck', exact: true}).click();
  const deck = page.getByLabel('Stream Deck-style control surface');
  await expect(deck.getByRole('button', {name: 'Select Agent 2', exact: true})).toHaveAttribute('aria-pressed', 'true');
  await expect(deck.getByRole('button', {name: 'Approve', exact: true})).toBeEnabled();
  expect(inputs).toHaveLength(0);
  await deck.getByRole('button', {name: 'Approve', exact: true}).click();
  const approval = {protocol: 1, type: 'action', action: 'approve', expected_revision: 12};
  await expect.poll(() => inputs.at(-1)).toEqual(approval);
  await expect.poll(() => (preferences as Record<string, unknown>).surface_layout).toBe('stream-deck');
  await page.reload();
  await expect(deck.getByRole('button', {name: 'Select Agent 2', exact: true})).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', {name: 'Maximize pad', exact: true}).click();
  await expect(layout.getByRole('button', {name: 'Grid', exact: true})).toBeVisible();
  await expect(deck).toBeVisible();
  const deckBounds = await deck.boundingBox();
  expect(deckBounds!.x + deckBounds!.width).toBeLessThanOrEqual(page.viewportSize()!.width);
  expect(deckBounds!.y + deckBounds!.height).toBeLessThanOrEqual(page.viewportSize()!.height);
  await page.screenshot({path: test.info().outputPath('stream-deck-maximized.png')});
  await page.getByRole('button', {name: 'Restore workspace', exact: true}).click();
  await layout.getByRole('button', {name: 'Grid', exact: true}).click();
  await expect(pad.getByRole('button', {name: 'Select Agent 2', exact: true})).toHaveAttribute('aria-pressed', 'true');
  expect(inputs).toEqual([approval]);

  await picker.click();
  await expect(picker).toHaveAttribute('aria-expanded', 'true');
  await page.getByRole('button', {name: 'Refresh chats', exact: true}).click();
  await expect(picker).toHaveAttribute('aria-expanded', 'true');
  await picker.press('Escape');
  await expect(picker).toHaveAttribute('aria-expanded', 'false');
  await expect(picker).toBeFocused();
  await pad.getByRole('button', {name: 'Select Agent 3', exact: true}).click();
  await expect(selected.getByRole('heading')).toHaveText('Agent 3');
  await expect(selected.getByRole('button', {name: 'Approve', exact: true})).toHaveCount(0);
  await expect(selected.getByRole('button', {name: 'Stop', exact: true})).toBeVisible();
  expect(inputs).toEqual([approval, {protocol: 1, type: 'select_session', slot: 2, expected_revision: 12}]);
  view = {...view, control_revision: 14, selected_state: 'error', available_actions: ['retry'],
    sessions: view.sessions.map(s => s.slot === 2 ? {...s, state: 'error'} : s)};
  await emitSurface(page, message());
  await layout.getByRole('button', {name: 'Stream Deck', exact: true}).click();
  await deck.getByRole('button', {name: 'Retry', exact: true}).click();
  await expect.poll(() => inputs.at(-1)).toEqual({protocol: 1, type: 'action', action: 'retry', expected_revision: 14});
  await layout.getByRole('button', {name: 'Grid', exact: true}).click();
  await expect(picker).toHaveAttribute('aria-expanded', 'false');

  await page.getByRole('button', {name: 'Settings', exact: true}).click();
  await page.getByRole('button', {name: 'Light', exact: true}).click();
  await page.getByRole('button', {name: 'Back to pad', exact: true}).click();
  await expect(pad).toBeVisible();
  await page.screenshot({path: test.info().outputPath('workspace-light.png')});
  await page.setViewportSize({width: 390, height: 844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await pad.getByRole('button', {name: 'Select Agent 8', exact: true}).click();
  await expect(selected.getByRole('heading')).toHaveText('Agent 8');
  await layout.getByRole('button', {name: 'Stream Deck Neo', exact: true}).click();
  await expect(deck.locator('.deckKey')).toHaveCount(8);
  await expect(deck.getByText('Page 2 / 2')).toBeVisible();
  await expect(deck.getByRole('button', {name: 'Select Agent 8', exact: true})).toHaveAttribute('aria-pressed', 'true');
  await page.screenshot({path: test.info().outputPath('neo-layout.png'), fullPage: true});
  await deck.getByRole('button', {name: 'Previous page'}).click();
  await expect(deck.getByText('Page 1 / 2')).toBeVisible();
  await expect(deck.getByRole('button', {name: 'Stop', exact: true})).toContainText('Agent 8');
  view = {...view, control_revision: 15, selected_state: 'error', available_actions: ['retry'],
    sessions: view.sessions.map(s => s.slot === 7 ? {...s, state: 'error'} : s)};
  await emitSurface(page, message());
  await deck.getByRole('button', {name: 'Retry Agent 8', exact: true}).click();
  await expect.poll(() => inputs.at(-1)).toEqual({protocol: 1, type: 'action', action: 'retry', expected_revision: 15});
  await deck.getByRole('button', {name: 'Select Agent 1', exact: true}).click();
  await expect.poll(() => inputs.at(-1)).toEqual({protocol: 1, type: 'select_session', slot: 0, expected_revision: 15});
  await expect(selected.getByRole('heading')).toHaveText('Agent 1');
  await layout.getByRole('button', {name: 'Stream Deck XL', exact: true}).click();
  await expect(deck.locator('.deckKey')).toHaveCount(32);
  await expect(deck.getByRole('button', {name: 'Select Agent 1', exact: true})).toHaveAttribute('aria-pressed', 'true');
  const overflow = await deck.locator('.deckKey button, .deckKey span').evaluateAll(elements => elements.some(el => {
    const box = el.getBoundingClientRect(), parent = el.closest('.deckKey')!.getBoundingClientRect();
    return box.width > 0 && (box.left < parent.left - 1 || box.right > parent.right + 1 || box.bottom > parent.bottom + 1);
  }));
  expect(overflow).toBe(false);
  await expect.poll(() => (preferences as Record<string, unknown>).surface_layout).toBe('stream-deck-xl');
  await page.screenshot({path: test.info().outputPath('workspace-narrow.png'), fullPage: true});
});
