import assert from 'node:assert/strict';
import {once} from 'node:events';
import test from 'node:test';
import {setTimeout as sleep} from 'node:timers/promises';
import {WebSocketServer, type WebSocket} from 'ws';
import {Bridge, bridgeOrigin, liveView, type LiveView} from '../src/bridge';
import {sessionImage, actionImage} from '../src/render';

export const view: LiveView = {
  selected_state: 'waiting_for_approval', frame: 0, activity_motion: false, overflow_count: 0,
  control_revision: 7, available_actions: ['approve', 'reject'],
  sessions: [{slot: 0, state: 'waiting_for_approval', selected: true, accent: 'cyan', label: 'Review'},
    {slot: 1, state: 'running', selected: false, accent: 'magenta', label: 'Tests'}],
};
export async function until(check: () => boolean, timeout = 4000) {
  const end = Date.now() + timeout;
  while (!check()) { if (Date.now() >= end) throw new Error('Timed out waiting for fixture'); await sleep(10); }
}
test('endpoint validation keeps credentials on explicit local/private addresses', () => {
  for (const url of ['http://127.0.0.1:8765', 'http://localhost:8765', 'http://192.168.1.45:8001', 'http://10.1.2.3:8765']) {
    assert.equal(bridgeOrigin(url), url);
  }
  for (const url of ['https://example.com', 'http://8.8.8.8', 'file:///tmp/key', 'http://127.0.0.1/#admin=secret',
    'http://user:secret@127.0.0.1', 'http://127.0.0.1/ws', 'http://127.0.0.1/?key=secret']) assert.throws(() => bridgeOrigin(url));
});
test('malformed or unguarded views cannot enable controls', () => {
  assert.ok(liveView(view));
  for (const v of [{...view, control_revision: null}, {...view, control_revision: -1},
    {...view, sessions: [view.sessions[0], view.sessions[0]]}, {...view, available_actions: ['shell']},
    {...view, sessions: [{...view.sessions[0], accent: 'url(bad)'}]}]) assert.equal(liveView(v), null);
});
test('session renderer reuses glyphs, escapes labels, and distinguishes selected keys', () => {
  const approval = sessionImage(view.sessions[0], 0, 'Connected');
  assert.match(approval, /#f0b63f/);
  assert.match(approval, /stroke="#ffffff"/);
  const unsafe = sessionImage({...view.sessions[0], label: '<script>&'}, 0, 'Connected');
  assert.ok(!unsafe.includes('<script>'));
  assert.match(unsafe, /&lt;script&gt;&amp;/);
  assert.match(actionImage('approve', view.sessions[0], false), /#657079/);
  assert.match(actionImage('approve', view.sessions[0], true), /#55c76a/);
});

test('paired bridge gates actions, reconnects with memory-only token, and clears revoked state', async t => {
  const server = new WebSocketServer({host: '127.0.0.1', port: 0});
  await once(server, 'listening');
  const address = server.address();
  assert.ok(address && typeof address !== 'string');
  const commands: Record<string, unknown>[] = [];
  let current: WebSocket;
  server.on('connection', (socket, request) => {
    current = socket;
    assert.equal(request.headers.origin, `http://127.0.0.1:${address.port}`);
    assert.equal(request.headers['user-agent'], 'pad-lattice-stream-deck');
    socket.on('message', raw => {
      const m = JSON.parse(raw.toString()); commands.push(m);
      if (m.type === 'authenticate') {
        socket.send(JSON.stringify({protocol: 1, type: 'authenticated', admin: false,
          session_token: m.credential === '123456' ? 'reconnect-secret' : null}));
        socket.send(JSON.stringify({protocol: 1, type: 'surface', visual_protocol: 1, view}));
      }
    });
  });
  const bridge = new Bridge(() => {});
  t.after(async () => { bridge.disconnect(); for (const c of server.clients) c.terminate(); await new Promise<void>(resolve => server.close(() => resolve())); });
  assert.equal(bridge.act('approve', 7), false);
  bridge.pair(`http://127.0.0.1:${address.port}`, '123456');
  await until(() => !!bridge.view);
  assert.equal(bridge.act('stop', 7), false);
  assert.equal(bridge.act('approve', 6), false);
  assert.equal(bridge.act('approve', 7), true);
  assert.equal(bridge.act('approve', 7), false);
  await until(() => commands.some(m => m.type === 'action'));
  assert.deepEqual(commands.find(m => m.type === 'action'), {protocol: 1, type: 'action', action: 'approve', expected_revision: 7});
  current!.terminate();
  await until(() => commands.filter(m => m.type === 'authenticate').length === 2);
  await until(() => !!bridge.view);
  assert.equal(commands.filter(m => m.type === 'authenticate')[1].credential, 'reconnect-secret');
  assert.equal(bridge.select(7, 7), false);
  assert.equal(bridge.select(1, 7), true);
  await until(() => commands.some(m => m.type === 'select_session'));
  current!.close(1008, 'revoked');
  await until(() => bridge.status === 'Pair device');
  assert.equal(bridge.view, null);
  assert.equal(bridge.act('approve', 7), false);
});

test('authentication rejection never enables actions or retries the PIN', async t => {
  const server = new WebSocketServer({host: '127.0.0.1', port: 0});
  await once(server, 'listening');
  const address = server.address(); assert.ok(address && typeof address !== 'string');
  let attempts = 0;
  server.on('connection', socket => socket.on('message', () => {
    attempts++;
    socket.send(JSON.stringify({protocol: 1, type: 'error', code: 'forbidden'}));
  }));
  const bridge = new Bridge(() => {});
  t.after(async () => { bridge.disconnect(); for (const c of server.clients) c.terminate(); await new Promise<void>(resolve => server.close(() => resolve())); });
  bridge.pair(`http://127.0.0.1:${address.port}`, '000000');
  await until(() => attempts === 1 && bridge.status === 'Pair device');
  assert.equal(bridge.connection, 'unpaired');
  assert.match(bridge.pairingError, /PIN expired or rejected/);
  await sleep(1200);
  assert.equal(attempts, 1);
  assert.equal(bridge.view, null);
});

test('failed first connection stops setup and a fresh pairing can succeed', async t => {
  const server = new WebSocketServer({host: '127.0.0.1', port: 0});
  await once(server, 'listening');
  const address = server.address(); assert.ok(address && typeof address !== 'string');
  let attempts = 0;
  server.on('connection', socket => socket.on('message', () => {
    attempts++;
    if (attempts === 1) socket.terminate();
    else socket.send(JSON.stringify({protocol: 1, type: 'authenticated', admin: false, session_token: 'paired-token'}));
  }));
  const bridge = new Bridge(() => {});
  t.after(async () => { bridge.disconnect(); for (const client of server.clients) client.terminate(); await new Promise<void>(resolve => server.close(() => resolve())); });
  bridge.pair(`http://127.0.0.1:${address.port}`, '123456');
  assert.equal(bridge.connection, 'connecting');
  await until(() => bridge.connection === 'unpaired');
  assert.match(bridge.pairingError, /Cannot reach/);
  await sleep(1200);
  assert.equal(attempts, 1);
  bridge.pair(`http://127.0.0.1:${address.port}`, '654321');
  await until(() => bridge.connection === 'connected');
  assert.equal(bridge.pairingError, '');
  assert.equal(bridge.act('approve', 7), false);
});

test('administrator disconnect stops automatic reconnection', async t => {
  const server = new WebSocketServer({host: '127.0.0.1', port: 0});
  await once(server, 'listening');
  const address = server.address(); assert.ok(address && typeof address !== 'string');
  let attempts = 0;
  server.on('connection', socket => socket.on('message', () => {
    attempts++;
    socket.send(JSON.stringify({protocol: 1, type: 'authenticated', admin: false, session_token: 'test-token'}));
    socket.send(JSON.stringify({protocol: 1, type: 'surface', visual_protocol: 1, view}));
    socket.send(JSON.stringify({protocol: 1, type: 'device_disconnected'}));
    socket.close(1000);
  }));
  const bridge = new Bridge(() => {});
  t.after(async () => { bridge.disconnect(); for (const client of server.clients) client.terminate(); await new Promise<void>(resolve => server.close(() => resolve())); });
  bridge.pair(`http://127.0.0.1:${address.port}`, '123456');
  await until(() => attempts === 1 && bridge.status === 'Disconnected');
  await sleep(1200);
  assert.equal(attempts, 1);
  assert.equal(bridge.view, null);
  assert.equal(bridge.act('approve', 7), false);
});
