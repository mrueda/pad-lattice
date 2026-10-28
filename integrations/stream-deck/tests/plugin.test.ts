import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {resolve} from 'node:path';
import {setTimeout as sleep} from 'node:timers/promises';
import test from 'node:test';
import {WebSocketServer, type WebSocket} from 'ws';

test('bundled SDK plugin registers, renders keys, pairs, and sends a guarded action', {timeout: 12000}, async t => {
  const elgato = new WebSocketServer({host: '127.0.0.1', port: 0});
  const lattice = new WebSocketServer({host: '127.0.0.1', port: 0});
  await Promise.all([once(elgato, 'listening'), once(lattice, 'listening')]);
  const port = (server: WebSocketServer) => (server.address() as {port: number}).port;
  const received: any[] = [], commands: any[] = [];
  let socket: WebSocket;
  const info = {application: {version: '7.1.0', platform: 'mac', language: 'en'},
    plugin: {uuid: 'io.github.mrueda.pad-lattice', version: '0.2.0.0'},
    devices: [{id: 'test-device', name: 'Test Deck', size: {columns: 5, rows: 3}, type: 0}]};
  elgato.on('connection', ws => {
    socket = ws;
    ws.on('message', raw => {
      const m = JSON.parse(raw.toString()); received.push(m);
      if (m.event === 'getGlobalSettings') ws.send(JSON.stringify({event: 'didReceiveGlobalSettings', id: m.id, payload: {settings: {}}}));
    });
  });
  lattice.on('connection', ws => ws.on('message', raw => {
    const m = JSON.parse(raw.toString()); commands.push(m);
    if (m.type === 'authenticate') {
      ws.send(JSON.stringify({protocol: 1, type: 'authenticated', admin: false, session_token: 'private-token'}));
      ws.send(JSON.stringify({protocol: 1, type: 'surface', visual_protocol: 1, view: {
        selected_state: 'waiting_for_approval', frame: 0, control_revision: 42,
        available_actions: ['approve', 'reject'], overflow_count: 0, activity_motion: false,
        sessions: [{slot: 0, state: 'waiting_for_approval', selected: true, accent: 'cyan', label: 'Review'}],
      }}));
    }
  }));
  const child = spawn(process.execPath, ['bin/plugin.js', '-port', String(port(elgato)), '-pluginUUID', 'test-plugin',
    '-registerEvent', 'registerPlugin', '-info', JSON.stringify(info)], {cwd: resolve('io.github.mrueda.pad-lattice.sdPlugin'), stdio: 'pipe'});
  let errors = ''; child.stderr.on('data', b => { errors += b; });
  const until = async (check: () => boolean) => {
    const end = Date.now() + 5000;
    while (!check()) { assert.equal(child.exitCode, null, errors); if (Date.now() > end) throw new Error('SDK fixture timed out: ' + errors); await sleep(10); }
  };
  t.after(async () => {
    child.kill(); await once(child, 'exit').catch(() => {});
    for (const server of [elgato, lattice]) { for (const c of server.clients) c.terminate(); await new Promise<void>(resolve => server.close(() => resolve())); }
  });
  await until(() => received.some(m => m.event === 'getGlobalSettings'));
  assert.ok(received.some(m => m.event === 'registerPlugin'));
  const event = (type: string, name: string, payload: object = {}) => socket!.send(JSON.stringify({event: type,
    action: `io.github.mrueda.pad-lattice.${name}`, context: name, device: 'test-device', payload}));
  for (const name of ['session', 'approve', 'reject', 'stop']) event('willAppear', name, {controller: 'Keypad', settings: {}, coordinates: {row: 0, column: 0}});
  await until(() => received.filter(m => m.event === 'setImage').length >= 4);
  event('propertyInspectorDidAppear', 'session');
  event('sendToPlugin', 'session', {type: 'pair', address: `http://127.0.0.1:${port(lattice)}`, pin: '123456'});
  const decoded = (m: any) => Buffer.from(m.payload.image.split(',')[1], 'base64').toString();
  await until(() => received.some(m => m.event === 'setImage' && m.context === 'approve' && decoded(m).includes('#55c76a')));
  await until(() => received.some(m => m.event === 'sendToPropertyInspector' && m.payload.connection === 'connected'));
  event('keyDown', 'approve', {controller: 'Keypad', settings: {}});
  await until(() => commands.some(m => m.type === 'action'));
  assert.deepEqual(commands.find(m => m.type === 'action'), {protocol: 1, type: 'action', action: 'approve', expected_revision: 42});
  for (const m of received.filter(m => ['setSettings', 'setGlobalSettings', 'sendToPropertyInspector'].includes(m.event))) {
    assert.ok(!JSON.stringify(m).includes('123456'));
    assert.ok(!JSON.stringify(m).includes('private-token'));
  }
});
