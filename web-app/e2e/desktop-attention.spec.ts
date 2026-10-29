import {test, expect} from '@playwright/test';
import {desktopBridge, emitDesktopEvent, emitSurface} from './desktopTestHarness';
import {compileVisualFrame} from '../src/surfaceModel';
import {accentNames, type SurfaceView} from '../src/types';

test('idle chats are Ready, questions need attention, and a removed Scene leaves a gap', async ({page}) => {
  let view: SurfaceView = {selected_state: 'idle', frame: 0, control_revision: 1,
    sessions: [{slot: 0, state: 'running', selected: false, accent: 'cyan', label: 'Builder'},
      {slot: 1, state: 'idle', selected: true, accent: 'magenta', label: 'Montessori'},
      {slot: 2, state: 'idle', selected: false, accent: 'lime', label: 'Portfolio'}],
    available_actions: [], overflow_count: 0, activity_motion: false};
  const surface = () => ({protocol: 1, type: 'surface', visual_protocol: 1, view, visual_frame: compileVisualFrame(view)});
  await desktopBridge(page, (method) => {
    if (method === 'settings') return {};
    if (method === 'status') return {version: '0.2.0', settings: {}, inputs: [], outputs: [], profiles: [], midi: null, lan_host: '127.0.0.1'};
    if (method === 'inspect_codex') return {available: true, version: '0.165.0', tested_version: '0.165.0'};
    if (method === 'paired_devices') return {devices: []};
    if (method === 'snapshot') return {messages: [{protocol: 1, type: 'authenticated', admin: true, lan_enabled: false}, surface()]};
    if (method === 'list_conversations') return {available: true, conversations: view.sessions.map(s => ({
      ...s, id: s.label, name: s.label, cwd: '/work', connected: true, managed: true}))};
    if (method === 'attention') return {revision: view.control_revision, overflow_count: 0,
      sessions: view.sessions.filter(s => s.state === 'waiting_for_reply').map(s => ({...s, age_seconds: 2}))};
    if (method === 'question_status') return {slot: 1, revision: view.control_revision, question: null};
    throw Error(`Unexpected request: ${method}`);
  });
  await page.goto('/');
  await expect(page.getByRole('tab', {name: 'Needs attention (0)'})).toBeVisible();
  await expect(page.locator('.sessionList .stateLabel').filter({hasText: 'Ready'})).toHaveCount(2);
  await expect(page.getByRole('button', {name: /Next needing attention/})).toHaveCount(0);
  await expect(page.getByRole('region', {name: 'Selected Codex conversation'}).locator('.stateLabel')).toHaveText('Ready');
  await page.screenshot({path: test.info().outputPath('ready-chats.png'), fullPage: true});
  view = {...view, control_revision: 2, selected_state: 'waiting_for_reply',
    sessions: view.sessions.map(s => ({...s, state: s.slot === 1 ? 'waiting_for_reply' : s.state}))};
  await emitSurface(page, surface());
  await expect(page.getByRole('tab', {name: 'Needs attention (1)'})).toBeVisible();
  view = {...view, control_revision: 3, selected_state: 'idle',
    sessions: view.sessions.map(s => ({...s, state: s.slot === 1 ? 'idle' : s.state}))};
  await emitSurface(page, surface());
  await expect(page.getByRole('tab', {name: 'Needs attention (0)'})).toBeVisible();
  view = {...view, control_revision: 4, selected_state: null,
    sessions: view.sessions.filter(s => s.slot !== 1)};
  await emitSurface(page, surface());
  await page.getByRole('button', {name: 'Refresh chats', exact: true}).click();
  await page.getByRole('button', {name: /Codex conversations/}).click();
  const picker = page.getByRole('region', {name: 'Codex conversations'});
  await expect(picker).not.toContainText('Montessori');
  await expect(picker.getByText('On pad, Scene 3', {exact: true})).toBeVisible();
  await expect(page.locator('.sessionList').getByRole('button', {name: 'Portfolio Scene 3'})).toBeVisible();
  await expect(page.locator('.sessionList .selected')).toHaveCount(0);
  await expect(page.getByRole('tab', {name: 'Needs attention (0)'})).toBeVisible();
});

test('approval details, next attention, and lost connections stay scoped', async ({page}) => {
  let view: SurfaceView = {selected_state: 'waiting_for_approval', frame: 0, control_revision: 10,
    sessions: [{slot: 0, state: 'waiting_for_approval', selected: true, accent: 'cyan', label: 'Builder'},
      {slot: 1, state: 'waiting_for_reply', selected: false, accent: 'lime', label: 'Reviewer'}],
    available_actions: ['approve', 'reject'], overflow_count: 0, activity_motion: false};
  let lost = false;
  let truncated = false;
  const actions: Record<string, unknown>[] = [];
  const surface = () => ({protocol: 1, type: 'surface', visual_protocol: 1, view, visual_frame: compileVisualFrame(view)});
  await desktopBridge(page, async (method, params) => {
    if (method === 'settings') return {};
    if (method === 'status') return {version: '0.2.0', settings: {}, inputs: [], outputs: [], profiles: [], midi: null, lan_host: '127.0.0.1'};
    if (method === 'inspect_codex') return {available: true, version: '0.165.0', tested_version: '0.165.0'};
    if (method === 'paired_devices') return {devices: []};
    if (method === 'snapshot') return {messages: [{protocol: 1, type: 'authenticated', admin: true, lan_enabled: false}, surface()]};
    if (method === 'list_conversations') return {available: true, conversations: [{id: 'a', name: 'Builder', cwd: '/work',
      state: 'approval', connected: !lost, managed: !lost, slot: lost ? null : 0, accent: 'cyan'}]};
    if (method === 'attention') return {revision: view.control_revision, overflow_count: 0,
      sessions: view.sessions.map((s, i) => ({...s, age_seconds: 90 + i}))};
    if (method === 'approval_status') return {slot: 0, revision: 10, approval: {kind: 'command', command: 'npm test',
      reason: 'Run checks', cwd: '/work', truncated, additional_permissions: false}};
    if (method === 'question_status') return {slot: 1, revision: 11, question: null};
    if (method === 'surface') {
      actions.push(params);
      if (params.type === 'select_session') {
        view = {...view, control_revision: 11, selected_state: 'waiting_for_reply', available_actions: ['stop'],
          sessions: view.sessions.map(s => ({...s, selected: s.slot === params.slot}))};
        await emitSurface(page, surface());
      }
      return {};
    }
    throw Error(`Unexpected request: ${method}`);
  });
  await page.goto('/');
  const approval = page.getByRole('region', {name: 'Approval request'});
  await expect(approval).toContainText('npm test');
  await expect(approval).toContainText('/work');
  await page.screenshot({path: test.info().outputPath('approval-context.png'), fullPage: true});
  truncated = true;
  await expect(approval).toContainText('Full details are not shown here');
  await page.getByRole('button', {name: /Next needing attention/}).click();
  await expect.poll(() => actions.at(-1)).toEqual({protocol: 1, type: 'select_session', slot: 1, expected_revision: 10});
  await expect(approval).toHaveCount(0);
  expect(actions).toHaveLength(1);
  lost = true;
  await emitDesktopEvent(page, 'pad-lattice-attachment', {thread_id: 'a'});
  await expect(page.getByText(/A Codex connection was lost/)).toBeVisible();
  await expect(page.getByRole('button', {name: 'Reconnect Builder'})).toBeVisible();
});

test('browser question sharing is opt-in and can be disabled', async ({page}) => {
  const settings: Record<string, unknown> = {};
  const view: SurfaceView = {selected_state: null, frame: 0, control_revision: 1, sessions: [],
    available_actions: [], overflow_count: 0, activity_motion: false};
  await desktopBridge(page, (method, params) => {
    if (method === 'settings') return Object.assign(settings, params);
    if (method === 'status') return {version: '0.2.0', settings, inputs: [], outputs: [], profiles: [], midi: null, lan_host: '127.0.0.1'};
    if (method === 'inspect_codex') return {available: true, version: '0.165.0', tested_version: '0.165.0'};
    if (method === 'paired_devices') return {devices: []};
    if (method === 'list_conversations') return {available: true, conversations: []};
    if (method === 'snapshot') return {messages: [{protocol: 1, type: 'authenticated', admin: true, lan_enabled: false},
      {protocol: 1, type: 'surface', visual_protocol: 1, view, visual_frame: compileVisualFrame(view)}]};
    throw Error(`Unexpected request: ${method}`);
  });
  await page.goto('/');
  await page.getByRole('button', {name: 'Settings', exact: true}).click();
  await page.getByRole('tab', {name: 'Devices', exact: true}).click();
  const sharing = page.getByRole('checkbox', {name: 'Share Codex questions with paired browsers'});
  await expect(sharing).not.toBeChecked();
  await expect(page.getByText(/Optional, off by default. Paired browsers can still show status/)).toBeVisible();
  await sharing.check();
  await expect.poll(() => settings.share_browser_questions).toBe(true);
  await sharing.uncheck();
  await expect.poll(() => settings.share_browser_questions).toBe(false);
});

test('eight chats stay navigable while child requests share their parent scene', async ({page}, testInfo) => {
  if (testInfo.project.name === 'desktop') await page.setViewportSize({width: 1280, height: 800});
  let view: SurfaceView = {selected_state: 'waiting_for_approval', frame: 0, control_revision: 20,
    sessions: accentNames.map((accent, slot) => ({slot, accent, selected: slot === 1,
      state: slot === 1 ? 'waiting_for_approval' : 'running',
      label: slot === 1 ? 'Build virtual Montessori classroom' : `Project ${slot + 1}: implementation and review`})),
    available_actions: ['stop'], overflow_count: 0, activity_motion: false};
  const actions: Record<string, unknown>[] = [];
  const surface = () => ({protocol: 1, type: 'surface', visual_protocol: 1, view, visual_frame: compileVisualFrame(view)});
  await desktopBridge(page, async (method, params) => {
    if (method === 'settings') return {};
    if (method === 'status') return {version: '0.2.0', settings: {}, inputs: [], outputs: [], profiles: [], midi: null, lan_host: '127.0.0.1'};
    if (method === 'inspect_codex') return {available: true, version: '0.165.0', tested_version: '0.165.0'};
    if (method === 'paired_devices') return {devices: []};
    if (method === 'list_conversations') return {available: true, conversations: []};
    if (method === 'snapshot') return {messages: [{protocol: 1, type: 'authenticated', admin: true, lan_enabled: false}, surface()]};
    if (method === 'attention') return {revision: view.control_revision, overflow_count: 0,
      sessions: view.sessions.filter(s => s.slot === 1).map(s => ({...s, age_seconds: 125, child_attention_count: 3}))};
    if (method === 'approval_status') return {slot: 1, revision: view.control_revision, approval: null,
      pending_count: 3, child_attention_count: 3};
    if (method === 'question_status') return {slot: null, revision: view.control_revision, question: null};
    if (method === 'surface') {
      actions.push(params);
      if (params.type === 'select_session') {
        view = {...view, control_revision: (view.control_revision ?? 20) + 1,
          selected_state: params.slot === 1 ? 'waiting_for_approval' : 'running',
          sessions: view.sessions.map(s => ({...s, selected: s.slot === params.slot}))};
        await emitSurface(page, surface());
      }
      return {};
    }
    throw Error(`Unexpected request: ${method}`);
  });
  await page.goto('/');
  await expect(page.getByText(/3 requests need attention, including child agents/)).toBeVisible();
  const list = page.locator('.sessionList');
  await expect(list.locator('.sessionRow')).toHaveCount(8);
  await expect(page.getByRole('tab', {name: 'Needs attention (1)'})).toBeVisible();
  await list.getByRole('button', {name: 'Project 8: implementation and review Scene 8'}).click();
  await expect.poll(() => actions.at(-1)?.slot).toBe(7);
  await page.getByRole('tab', {name: 'Needs attention (1)'}).click();
  await expect(page.getByText('3 child agents need attention')).toBeVisible();
  await page.getByRole('button', {name: 'Select Build virtual Montessori classroom'}).click();
  await expect.poll(() => actions.at(-1)?.slot).toBe(1);
  await expect(page.getByText(/3 requests need attention, including child agents/)).toBeVisible();
  expect(actions.every(action => action.type === 'select_session')).toBe(true);
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({path: test.info().outputPath('eight-chats-attention.png'), fullPage: true});
  await page.getByRole('tab', {name: 'All conversations'}).click();
  await page.screenshot({path: test.info().outputPath('eight-chats-list.png'), fullPage: true});
});
