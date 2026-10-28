import {test, expect} from '@playwright/test';
import {desktopBridge, emitSurface} from './desktopTestHarness';
import {compileVisualFrame} from '../src/surfaceModel';
import type {SurfaceView} from '../src/types';

test('Devices groups MIDI, Stream Deck and browsers without mixing their configuration', async ({page}) => {
  const calls: Array<{method: string; params: Record<string, unknown>}> = [];
  const preferences: Record<string, unknown> = {};
  let pairingOrigin = 'http://127.0.0.1:8765';
  let devices = [
    {id: 'phone-123456', name: 'Android / Chrome', kind: 'browser', connected: true},
    {id: 'deck-654321', name: 'Elgato Stream Deck', kind: 'stream_deck', connected: true},
  ];
  const view: SurfaceView = {selected_state: null, frame: 0, sessions: [], available_actions: [], overflow_count: 0, activity_motion: false};
  await desktopBridge(page, async (method, params) => {
    calls.push({method, params});
    if (method === 'settings') return Object.assign(preferences, params);
    if (method === 'paired_devices') return {devices};
    if (method === 'list_conversations') return {available: true, conversations: []};
    if (method === 'inspect_codex') return {available: true, version: '0.165.0', tested_version: '0.165.0'};
    if (method === 'status') return {version: '0.2.0', settings: preferences, inputs: [], outputs: [], profiles: [], midi: null, lan_host: '127.0.0.1'};
    if (method === 'snapshot') return {messages: [{protocol: 1, type: 'authenticated', admin: true, lan_enabled: false},
      {protocol: 1, type: 'surface', visual_protocol: 1, view, visual_frame: compileVisualFrame(view)}]};
    if (method === 'profile_test_status') return null;
    if (method === 'open_project_link') return;
    if (method === 'surface') {
      expect(params.type).toBe('create_pairing');
      await emitSurface(page, {protocol: 1, type: 'pairing', pin: '123456', pairing_url: `${pairingOrigin}/#pair=fixture`,
        qr_data_uri: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="132" height="132"/%3E', expires_in: 300});
      return {};
    }
    if (method === 'disconnect_device') {
      expect(params.device_id).toBe('deck-654321');
      devices = devices.map(device => device.id === params.device_id ? {...device, connected: false} : device);
      return {devices};
    }
    if (method === 'revoke_device') {
      expect(params.device_id).toBe('deck-654321');
      devices = devices.filter(device => device.id !== params.device_id);
      return {devices};
    }
    throw Error(`Unexpected operation: ${method}`);
  });
  await page.goto('/');
  await page.getByRole('button', {name: '2 devices connected', exact: true}).click();
  const settings = page.getByRole('tablist', {name: 'Settings sections'});
  await expect(settings.getByRole('tab', {name: 'Devices', exact: true})).toHaveAttribute('aria-selected', 'true');
  await expect(settings.getByRole('tab', {name: /MIDI|Phones/})).toHaveCount(0);
  const types = page.getByRole('tablist', {name: 'Device types'});
  const paired = page.getByRole('region', {name: 'Paired devices'});
  await expect(paired).toContainText('Android / Chrome');
  await expect(paired).not.toContainText('Elgato Stream Deck');
  await types.getByRole('tab', {name: 'MIDI controllers', exact: true}).click();
  await expect(page.getByLabel('Profile', {exact: true})).toBeVisible();
  await expect(page.getByRole('button', {name: 'Start hardware test'})).toBeVisible();
  await expect(paired).toHaveCount(0);
  await types.getByRole('tab', {name: 'MIDI controllers', exact: true}).press('ArrowRight');
  await expect(types.getByRole('tab', {name: 'Stream Deck', exact: true})).toBeFocused();
  await expect(page.getByRole('heading', {name: 'Elgato Stream Deck', exact: true})).toBeVisible();
  await expect(page.getByText('Not yet available', {exact: true})).toBeVisible();
  await expect(page.getByRole('button', {name: 'Start hardware test'})).toHaveCount(0);
  await expect(paired).toContainText('Elgato Stream Deck');
  await expect(paired).not.toContainText('Android / Chrome');
  await page.getByRole('button', {name: 'Plugin setup guide'}).click();
  expect(calls.find(call => call.method === 'open_project_link')?.params.destination).toBe('stream-deck');
  await page.getByRole('button', {name: 'Get plugin', exact: true}).click();
  expect(calls.some(call => call.method === 'open_project_link' && call.params.destination === 'downloads')).toBe(true);
  await page.getByRole('button', {name: 'Pair device', exact: true}).click();
  const pairing = page.getByRole('dialog', {name: 'Pair Stream Deck'});
  await expect(pairing).toContainText('123456');
  await expect(pairing.locator('img')).toHaveCount(0);
  await expect(pairing.getByLabel('Pad-Lattice address')).toHaveValue('http://127.0.0.1:8765');
  await expect(pairing).toContainText('All keys share the connection');
  await page.screenshot({path: test.info().outputPath('stream-deck-pairing.png'), fullPage: true});
  await page.keyboard.press('Escape');
  pairingOrigin = 'http://192.168.1.43:8001';
  await page.getByRole('button', {name: 'Pair device', exact: true}).click();
  await expect(pairing.getByLabel('Pad-Lattice address')).toHaveValue(pairingOrigin);
  await expect(pairing.locator('img')).toHaveCount(0);
  await expect(pairing).not.toContainText('Same computer only');
  await page.keyboard.press('Escape');
  await page.locator('.networkSetup summary').click();
  await page.screenshot({path: test.info().outputPath('devices-stream-deck-dark.png'), fullPage: true});
  await settings.getByRole('tab', {name: 'Appearance & sound'}).click();
  await page.getByRole('button', {name: 'Light', exact: true}).click();
  await settings.getByRole('tab', {name: 'Devices', exact: true}).click();
  await page.screenshot({path: test.info().outputPath('devices-stream-deck-light.png'), fullPage: true});
  await page.getByRole('button', {name: 'Disconnect Elgato Stream Deck'}).click();
  await expect(paired).toContainText('Offline');
  await page.getByRole('button', {name: 'Revoke access for Elgato Stream Deck'}).click();
  await page.getByRole('button', {name: 'Revoke access', exact: true}).click();
  await expect(page.getByText('No Stream Deck paired', {exact: true})).toBeVisible();
  await types.getByRole('tab', {name: 'Browsers', exact: true}).click();
  await expect(paired).toContainText('Android / Chrome');
  await expect(paired).toContainText('Connected');
  expect(calls.some(call => call.method === 'connect_midi' || call.method === 'profile_test_start')).toBe(false);
});
