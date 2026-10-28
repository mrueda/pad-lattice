import {test, expect} from '@playwright/test';
import {desktopBridge} from './desktopTestHarness';
import {compileVisualFrame} from '../src/surfaceModel';
import type {SurfaceView} from '../src/types';

test('first-use setup distinguishes missing Codex, empty discovery, and unconnected chats', async ({page}) => {
  let installed = false;
  let open = false;
  let failCheck = false;
  const methods: string[] = [];
  const view: SurfaceView = {selected_state: null, sessions: [], available_actions: [],
    frame: 0, overflow_count: 0, activity_motion: false};
  await desktopBridge(page, async (method, params) => {
    methods.push(method);
    if (method === 'settings') {expect(params).toEqual({}); return {};}
    if (method === 'status') return {version: '0.2.0', settings: {}, inputs: [], outputs: [], profiles: [], midi: null, lan_host: '127.0.0.1'};
    if (method === 'inspect_codex') {
      if (failCheck) throw Error('Codex check failed');
      return {available: installed, version: installed ? '0.165.0' : undefined, tested_version: '0.165.0',
        error: installed ? undefined : 'Codex executable not found'};
    }
    if (method === 'list_conversations') return {available: installed, conversations: open ? [
      {id: 'review', name: 'Review', cwd: '/fixture', state: 'approval'},
      {id: 'tests', name: 'Tests', cwd: '/fixture', state: 'running', connected: true, launcher: true, slot: 0},
    ] : []};
    if (method === 'paired_devices') return {devices: []};
    if (method === 'attach_conversation') throw Error('Conversation is no longer available');
    if (method === 'snapshot') return {messages: [{protocol: 1, type: 'authenticated', admin: true, lan_enabled: false},
      {protocol: 1, type: 'surface', visual_protocol: 1, view, visual_frame: compileVisualFrame(view)}]};
    throw Error(`Unexpected method: ${method}`);
  });
  await page.goto('/');
  const list = page.getByRole('region', {name: 'Open Codex conversations'});
  await expect(list.getByText('Codex CLI not available')).toBeVisible();
  await page.getByRole('button', {name: 'Codex settings', exact: true}).click();
  const panel = page.locator('#settings-panel');
  await expect(panel.getByRole('status')).toContainText('Codex CLI not available');
  installed = true;
  await page.getByRole('button', {name: 'Check again', exact: true}).click();
  await expect(panel.getByRole('status')).toContainText('Codex CLI available');
  await expect(page.getByText('Codex executable not found', {exact: true})).toHaveCount(0);
  await page.screenshot({path: test.info().outputPath('codex-setup-ready.png'), fullPage: true});
  failCheck = true;
  await page.getByRole('button', {name: 'Check again', exact: true}).click();
  await expect(panel.getByRole('status')).toContainText('Codex CLI not available');
  await expect(page.getByRole('alert')).toContainText('Codex check failed');
  failCheck = false;
  await page.getByRole('button', {name: 'Check again', exact: true}).click();
  await expect(panel.getByRole('status')).toContainText('Codex CLI available');
  await page.getByRole('button', {name: 'Back to pad', exact: true}).click();
  await page.getByRole('button', {name: 'Refresh chats', exact: true}).click();
  await expect(list.getByText('No open Codex conversations')).toBeVisible();
  open = true;
  await page.getByRole('button', {name: 'Refresh chats', exact: true}).click();
  await expect(list.getByText('2 open · 1 connected to the pad')).toBeVisible();
  await page.getByRole('button', {name: 'Connect Review', exact: true}).click();
  await expect(list.getByRole('alert')).toContainText('Conversation is no longer available');
  await list.getByRole('button', {name: 'Diagnostics', exact: true}).click();
  await expect(page.getByRole('tab', {name: 'About', exact: true})).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('button', {name: 'Copy diagnostics'})).toBeVisible();
  expect(methods.filter(method => method === 'attach_conversation')).toHaveLength(1);
  expect(methods).not.toContain('launch_session');
});
