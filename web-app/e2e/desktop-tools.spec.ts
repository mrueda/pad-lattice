import {test, expect} from '@playwright/test';
import {desktopBridge, emitSurface} from './desktopTestHarness';
import {compileVisualFrame} from '../src/surfaceModel';
import {accentNames, controlActions, type AgentState, type SurfaceView} from '../src/types';

const idle: SurfaceView = {selected_state: null, frame: 0, sessions: [], available_actions: [],
  overflow_count: 0, activity_motion: false, control_revision: 0};
const message = (view: SurfaceView) => ({protocol: 1, type: 'surface', visual_protocol: 1, view, visual_frame: compileVisualFrame(view)});
const common = (method: string, view = idle) => {
  if (method === 'settings') return {};
  if (method === 'paired_devices') return {devices: []};
  if (method === 'list_conversations') return {available: true, conversations: []};
  if (method === 'inspect_codex') return {available: true, version: '0.165.0', tested_version: '0.165.0'};
  if (method === 'snapshot') return {messages: [{protocol: 1, type: 'authenticated', admin: true, lan_enabled: false}, message(view)]};
  throw Error(`Unexpected method ${method}`);
};

test('hardware wizard confirms lights, waits for physical input, exports and cancels on exit', async ({page}) => {
  const methods: string[] = [];
  const states: Array<AgentState | null> = [null, 'running', 'waiting_for_reply', 'user_typing', 'waiting_for_approval', 'success', 'error', 'cancelled'];
  const descriptions: Record<string, string> = {idle: 'Dim three-pad idle dash', running: 'Steady blue ellipsis',
    waiting_for_reply: 'White question mark', user_typing: 'Cyan chevron', waiting_for_approval: 'Restrained amber exclamation mark',
    success: 'Green happy face', error: 'Red X', cancelled: 'Gray hollow square', overflow: 'One steady amber overflow indicator'};
  const steps = [
    ...states.map(state => ({group: 'visual', key: state ?? 'idle', view: {...idle, selected_state: state}})),
    {group: 'visual', key: 'overflow', view: {...idle, overflow_count: 1}},
    ...controlActions.map(action => ({group: 'actions', key: action, view: {...idle, selected_state: 'waiting_for_reply' as const, available_actions: [action]}})),
    ...accentNames.map((_, slot) => ({group: 'selectors', key: String(slot + 1), view: {...idle,
      sessions: accentNames.map((accent, index) => ({slot: index, state: 'running' as const, selected: index === slot, accent, label: ''}))}})),
  ];
  let index = 0;
  let started = false;
  let cancelled = false;
  const results: Record<string, Record<string, boolean>> = {visual: {}, actions: {}, selectors: {}};
  const advance = (passed: boolean) => { const step = steps[index++]; results[step.group][step.key] = passed; };
  const snapshot = () => {
    if (!started) return null;
    const step = steps[index];
    return {run_id: 'fixture-run', status: cancelled ? 'cancelled' : step ? 'running' : 'completed', index: index + 1, total: 21,
      failure_stage: cancelled ? 'cancelled' : null, last_result: null, results,
      step: step && !cancelled ? {id: `${step.group}:${step.key}`, group: step.group, key: step.key,
        prompt: step.group === 'visual' ? descriptions[step.key] : `Press ${step.key}`, seconds_left: step.group === 'visual' ? null : 15} : null,
      surface: step && !cancelled ? message(step.view) : null};
  };
  await desktopBridge(page, (method, params) => {
    methods.push(method);
    if (method === 'status') return {version: '0.2.0', settings: {}, inputs: ['Test input'], outputs: ['Test output'],
      profiles: [{id: 'novation/launchpad/pro-mk1', status: 'supported'}], midi: null, lan_host: '127.0.0.1'};
    if (method === 'profile_test_status') return snapshot();
    if (method === 'profile_test_start') {
      expect(params).toEqual({profile: 'novation/launchpad/pro-mk1', input: 'Test input', output: 'Test output', confirmed: true});
      index = 0; started = true; cancelled = false; return snapshot();
    }
    if (method === 'profile_test_answer') {
      expect(params.step_id).toBe(`${steps[index].group}:${steps[index].key}`);
      advance(Boolean(params.passed)); return snapshot();
    }
    if (method === 'profile_test_cancel') { cancelled = true; return snapshot(); }
    if (method === 'save_profile_report') { expect(params.runId).toBe('fixture-run'); return true; }
    return common(method);
  });
  await page.goto('/');
  await page.getByRole('button', {name: 'MIDI: not connected'}).click();
  await expect(page.getByRole('button', {name: 'Start hardware test'})).toBeDisabled();
  await page.getByLabel('Profile', {exact: true}).selectOption('novation/launchpad/pro-mk1');
  await page.getByLabel('Input', {exact: true}).selectOption('Test input');
  await page.getByLabel('Output', {exact: true}).selectOption('Test output');
  await page.getByRole('checkbox', {name: 'These ports belong to my controller'}).check();
  await page.getByRole('button', {name: 'Start hardware test'}).click();
  await expect(page.getByText('Step 1 of 21')).toBeVisible();
  await expect(page.getByLabel('Profile', {exact: true})).toBeDisabled();
  await expect(page.getByRole('button', {name: 'Connect', exact: true})).not.toBeVisible();
  for (let i = 0; i < 9; i++) {
    await expect(page.getByText(`Step ${i + 1} of 21`)).toBeVisible();
    if (i === 4) await page.screenshot({path: test.info().outputPath('hardware-visual.png'), fullPage: true});
    await page.getByRole('button', {name: 'Matches', exact: true}).click();
  }
  await expect(page.getByText('Waiting for controller: 15s')).toBeVisible();
  await expect(page.getByRole('button', {name: 'Matches', exact: true})).toHaveCount(0);
  await page.screenshot({path: test.info().outputPath('hardware-input.png'), fullPage: true});
  for (let i = 9; i < 21; i++) {
    await expect(page.getByText(`Step ${i + 1} of 21`)).toBeVisible();
    advance(true);
  }
  await expect(page.getByText('All checks passed', {exact: true})).toBeVisible();
  await expect(page.getByText('21 of 21 checks passed')).toBeVisible();
  await page.getByRole('button', {name: 'Export report'}).click();
  await expect(page.getByText('Report saved')).toBeVisible();
  await page.getByRole('button', {name: 'Run again'}).click();
  await expect(page.getByText('Step 1 of 21')).toBeVisible();
  await page.getByRole('button', {name: 'Back to pad'}).click();
  await expect.poll(() => cancelled).toBe(true);
  expect(methods).not.toContain('surface');
  expect(methods).not.toContain('attach_conversation');
});

test('attention selects the named conversation, preserves age and handles unavailable status', async ({page}) => {
  const commands: Record<string, unknown>[] = [];
  let fail = false;
  let view: SurfaceView = {...idle, selected_state: 'running', control_revision: 7, sessions: [
    {slot: 0, label: 'Implementation', state: 'running', selected: true, accent: 'cyan'},
    {slot: 1, label: 'Review changes', state: 'waiting_for_approval', selected: false, accent: 'magenta'},
    {slot: 2, label: 'Documentation', state: 'waiting_for_reply', selected: false, accent: 'lime'},
  ]};
  await desktopBridge(page, async (method, params) => {
    if (method === 'status') return {version: '0.2.0', settings: {}, inputs: [], outputs: [], profiles: [], midi: null, lan_host: '127.0.0.1'};
    if (method === 'attention') {
      if (fail) throw Error('Test service unavailable');
      return {revision: view.control_revision, overflow_count: 0,
        sessions: view.sessions.filter(session => session.state !== 'running').map(session => ({...session, age_seconds: 75}))};
    }
    if (method === 'surface') {
      commands.push(params);
      expect(params).toEqual({protocol: 1, type: 'select_session', slot: 1, expected_revision: 7});
      view = {...view, selected_state: 'waiting_for_approval', control_revision: 8, available_actions: ['approve', 'reject'],
        sessions: view.sessions.map(session => ({...session, selected: session.slot === 1}))};
      await emitSurface(page, message(view));
      return {};
    }
    return common(method, view);
  });
  await page.goto('/');
  await page.getByRole('tab', {name: 'Needs attention (2)'}).click();
  const rows = page.locator('.attentionRow');
  await expect(rows).toHaveCount(2);
  await expect(rows.first()).toContainText('Review changes');
  await expect(rows.first()).toContainText('1m 15s');
  await rows.first().click();
  await expect(rows.first()).toHaveAttribute('aria-pressed', 'true');
  await expect(rows.first()).toContainText('1m 15s');
  await expect(page.locator('.selectedConversation')).toContainText('Review changes');
  await page.screenshot({path: test.info().outputPath('attention.png'), fullPage: true});
  expect(commands).toHaveLength(1);
  expect(commands[0].type).toBe('select_session');
  fail = true;
  await expect(page.getByText('Attention list unavailable. Reconnecting...')).toBeVisible();
  await expect(rows).toHaveCount(0);
  fail = false;
  await expect(rows).toHaveCount(2);
  await page.getByRole('tab', {name: 'All conversations'}).click();
  await expect(page.locator('.sessionRow')).toHaveCount(3);
});
