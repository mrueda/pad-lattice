/** Record the real desktop renderer/control plane with simulated agents and hardware. */
import {createRequire} from 'node:module';
import {spawn, execFileSync} from 'node:child_process';
import {createServer} from 'node:http';
import {createConnection} from 'node:net';
import {createInterface} from 'node:readline';
import {mkdtemp, mkdir, readFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(root, 'web-app/package.json'));
const {chromium} = require('@playwright/test');
const {MousePointer2} = require('lucide-react');
const {createElement} = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const pointerSvg = renderToStaticMarkup(createElement(MousePointer2, {size: 46, fill: 'white', stroke: '#10151a', strokeWidth: 1.5}));
const temporary = await mkdtemp(path.join(tmpdir(), 'pl-film-'));
const socketPath = path.join(temporary, 'agent.sock');
const output = path.join(root, 'docs-site/static/media');
await mkdir(output, {recursive: true});
const engine = spawn(path.join(root, '.venv/bin/python'), ['-m', 'pad_lattice.desktop_entry',
  'service', '--settings-dir', path.join(temporary, 'settings'), '--socket', socketPath], {cwd: root, stdio: ['pipe', 'pipe', 'pipe']});
engine.stderr.on('data', () => {});
const pending = new Map();
let sequence = 0;
let page;
let connected = false;
const conversations = [
  {id: 'film-build', name: 'Implementation'},
  {id: 'film-review', name: 'Review'},
  {id: 'film-tests', name: 'Tests'},
];
const attached = new Map();
let approved = false;
let browser;
const subscribers = [];
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
let resolveReady, rejectReady;
const ready = new Promise((resolve, reject) => {resolveReady = resolve; rejectReady = reject;});
engine.on('error', rejectReady);
engine.on('exit', code => rejectReady(Error(`Desktop engine exited: ${code}`)));
const lines = createInterface({input: engine.stdout});
lines.on('line', line => {
  const message = JSON.parse(line);
  if (message.event === 'ready') resolveReady();
  if (message.event === 'fatal') rejectReady(Error(message.error));
  if (message.id && pending.has(message.id)) {
    const request = pending.get(message.id); pending.delete(message.id); clearTimeout(request.timer);
    message.error ? request.reject(Error(message.error)) : request.resolve(message.result);
  }
  if (message.event === 'surface' && page && !page.isClosed()) {
    page.evaluate(payload => window.__filmEmit?.('pad-lattice-surface', payload), message.payload).catch(() => {});
  }
});
function rpc(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => {pending.delete(id); reject(Error(`Timed out: ${method}`));}, 12000);
    pending.set(id, {resolve, reject, timer});
    engine.stdin.write(JSON.stringify({id, method, params}) + '\n');
  });
}
async function state(id, state, label) {
  await new Promise((resolve, reject) => {
    const connection = createConnection(socketPath);
    connection.setTimeout(5000, () => connection.destroy(Error('State update timed out')));
    connection.on('error', reject);
    connection.on('connect', () => connection.write(JSON.stringify({protocol: 1, type: 'state', state,
      agent: {backend: 'codex', session_id: id, label}, reply: true}) + '\n'));
    connection.once('data', () => {connection.end(); resolve();});
  });
}
async function approval() {
  const connection = createConnection(socketPath);
  subscribers.push(connection);
  await new Promise((resolve, reject) => {connection.once('connect', resolve); connection.once('error', reject);});
  connection.write(JSON.stringify({protocol: 1, type: 'subscribe_actions', agent: {backend: 'codex', session_id: 'film-review'},
    actions: ['approve', 'reject'], request_id: 'film-request', one_shot: true}) + '\n');
  const reader = createInterface({input: connection});
  reader.on('line', async line => {
    if (JSON.parse(line).type !== 'action') return;
    approved = true;
    await state('film-review', 'running', 'Review');
    await pause(1400);
    await state('film-review', 'success', 'Review');
  });
}
const assetRoot = path.join(root, 'src/pad_lattice/web_dist/play');
const server = createServer(async (request, response) => {
  try {
    const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    const filename = path.resolve(assetRoot, '.' + (pathname === '/' ? '/index.html' : pathname));
    if (!filename.startsWith(assetRoot + path.sep)) throw Error('Invalid path');
    const body = await readFile(filename);
    const mime = {'.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.json': 'application/json', '.wav': 'audio/wav'};
    response.writeHead(200, {'Content-Type': mime[path.extname(filename)] ?? 'application/octet-stream'}); response.end(body);
  } catch {response.writeHead(404); response.end();}
});
try {
  await ready;
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  browser = await chromium.launch({headless: true, ...(process.env.PLAYWRIGHT_CHROMIUM_PATH ? {executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH} : {})});
  const context = await browser.newContext({viewport: {width: 1600, height: 1000}, deviceScaleFactor: 1,
    recordVideo: {dir: temporary, size: {width: 1600, height: 1000}}});
  page = await context.newPage();
  await page.exposeFunction('__filmRpc', async (command, args) => {
    if (command === 'choose_path') return '/projects/website';
    if (command !== 'desktop_request') throw Error(command);
    if (args.method === 'inspect_codex') return {available: true, version: '0.164.0', tested: true, tested_version: '0.164.0'};
    if (args.method === 'list_conversations') {
      const snapshot = await rpc('snapshot');
      const sessions = snapshot.messages.find(message => message.type === 'surface').view.sessions;
      return {available: true, conversations: conversations.map(item => {
        const session = sessions.find(session => session.slot === attached.get(item.id));
        return {...item, cwd: '/projects/website', state: session?.state === 'waiting_for_approval' ? 'approval' : 'running',
          connected: attached.has(item.id), managed: attached.has(item.id), slot: attached.get(item.id), accent: session?.accent};
      })};
    }
    if (args.method === 'attach_conversation') {
      const item = conversations.find(item => item.id === args.params.thread_id);
      if (!item) throw Error('Unknown simulated conversation');
      const slot = attached.size;
      await state(item.id, 'running', item.name);
      attached.set(item.id, slot);
      return {slot};
    }
    if (args.method === 'connect_midi') connected = true;
    if (args.method === 'disconnect_midi') connected = false;
    if (['status', 'connect_midi', 'disconnect_midi'].includes(args.method)) {
      const result = await rpc('status');
      return {...result, midi: connected ? 'novation/launchpad/pro-mk1' : null, midi_error: null};
    }
    return rpc(args.method, args.params);
  });
  await page.addInitScript(() => {
    const callbacks = new Map(), events = new Map(); let id = 0;
    window.__TAURI_INTERNALS__ = {
      transformCallback: callback => {callbacks.set(++id, callback); return id;},
      unregisterCallback: callback => callbacks.delete(callback),
      invoke: async (command, args) => {
        if (command === 'plugin:event|listen') {events.set(args.handler, args.event); return args.handler;}
        if (command === 'plugin:event|unlisten') {events.delete(args.eventId); return;}
        return window.__filmRpc(command, args);
      },
    };
    window.__TAURI_EVENT_PLUGIN_INTERNALS__ = {unregisterListener: (_event, id) => events.delete(id)};
    window.__filmEmit = (event, payload) => events.forEach((name, id) => {
      if (name === event) callbacks.get(id)?.({event, id, payload});
    });
  });
  await page.goto(`http://127.0.0.1:${server.address().port}`);
  await page.locator('.desktopControls').waitFor();
  await page.addStyleTag({content: `
    html, body {background:#edf2f5!important; overflow:hidden; color-scheme:light;}
    .desktopApp {position:fixed; left:26px; top:135px; width:1030px; height:800px; border:1px solid #8d9aa5; border-radius:8px; box-shadow:0 8px 30px #19354322; color-scheme:dark;}
    .desktopApp .workspace {grid-template-columns:minmax(0,1.2fr) minmax(290px,.8fr);}
    .desktopApp .virtualSurface {width:min(100%,270px);}
    .desktopApp .contextPane {padding:20px;}
    .desktopApp .desktopNotice {font-size:12px;}
    #filmCaption {position:fixed;left:30px;top:26px;color:#152735;font:600 30px/1.25 system-ui; margin:0; max-width:1220px;}
    #filmDetail {position:fixed;left:30px;top:76px;color:#435766;font:18px system-ui;margin:0;}
    #filmLabel {position:fixed;right:28px;bottom:22px;color:#596e7c;font:12px system-ui;letter-spacing:1px;}
    #controller {position:fixed;right:28px;top:266px;width:460px;opacity:.26;transition:opacity .7s;}
    #controller .virtualSurface {position:relative;width:460px;padding:22px 22px 55px 52px;background:#1a2024;border:5px solid #303a43;box-shadow:0 12px 0 #0c1014,0 22px 26px #13283933;border-radius:14px;}
    #controller .surfaceBody {position:relative;}
    #controller .railControl,#controller .sceneControl {border-radius:50%;}
    #controller .matrixPad {border-radius:3px;}
    #controller .reservedLeft {position:absolute;left:-36px;top:0;bottom:0;width:26px;display:grid;grid-template-rows:repeat(8,1fr);gap:8px;align-items:center;}
    #controller .reservedBottom {position:absolute;left:0;right:calc(100% / 9 + 8px);bottom:-38px;height:26px;display:grid;grid-template-columns:repeat(8,1fr);gap:8px;justify-items:center;}
    #controller .reservedLeft span,#controller .reservedBottom span {display:block;width:24px;height:24px;border-radius:50%;border:1px solid #606b73;background:#10161c;}
    #controller .surfaceCaption {font-size:10px;}
    #controller .surfaceCaption span:first-child {font-size:0;}
    #controller .surfaceCaption span:first-child:after {content:'novation  /  Launchpad Pro';font:600 12px system-ui; color:#d7e3e9;}
    #controller .surfaceCaption span:last-child {display:none;}
    #controller .surfaceFooter {display:none;}
    #controller button {cursor:pointer;}
    #controllerLabel {position:fixed;right:28px;top:197px;width:460px;text-align:center;font:600 20px system-ui;color:#213c4c;}
    #cable {position:fixed;left:1056px;top:525px;width:57px;height:5px;background:#748c97;}
    #cable.on {background:#1a8a80;box-shadow:0 0 8px #1a8a8033;}
    #cable:after {content:'USB MIDI';position:absolute;top:-24px;left:-8px;font:10px system-ui;white-space:nowrap;color:#496473;}
    .filmPress {outline:4px solid white!important;outline-offset:3px;}
    #filmPointer {position:fixed;z-index:100;pointer-events:none;display:none;filter:drop-shadow(0 2px 2px #0008);}
    #filmTarget {position:fixed;z-index:99;pointer-events:none;display:none;border:4px solid #fff;outline:2px solid #111;border-radius:8px;}
    #filmTargetLabel {position:fixed;z-index:101;pointer-events:none;display:none;background:#fff;color:#17252c;border:2px solid #17252c;border-radius:4px;padding:7px 12px;font:600 18px system-ui;}
  `});
  await page.evaluate(pointerSvg => {
    for (const [id, tag, text] of [['filmCaption','h1','Connect your open Codex conversations.'], ['filmDetail','p','One app for the on-screen pad, MIDI controller, and phone pairing.'], ['filmLabel','p','SIMULATED CODEX SESSIONS + ILLUSTRATED MIDI CONTROLLER'], ['controllerLabel','p','Optional: connect a Launchpad'], ['controller','div',''], ['cable','div','']]) {
      const element = document.createElement(tag); element.id = id; element.textContent = text; document.body.append(element);
    }
    for (const id of ['filmPointer', 'filmTarget', 'filmTargetLabel']) {
      const element = document.createElement('div'); element.id = id; document.body.append(element);
    }
    document.querySelector('#filmPointer').innerHTML = pointerSvg;
    const source = document.querySelector('.desktopApp .virtualSurface');
    const target = document.querySelector('#controller');
    const sync = () => {
      target.innerHTML = source.outerHTML;
      for (const className of ['reservedLeft', 'reservedBottom']) {
        const rail = document.createElement('div'); rail.className = className; rail.setAttribute('aria-hidden', 'true');
        for (let i = 0; i < 8; i++) rail.append(document.createElement('span'));
        target.querySelector('.surfaceBody').append(rail);
      }
    }; sync();
    new MutationObserver(sync).observe(source, {attributes: true, childList: true, subtree: true, characterData: true});
    target.addEventListener('click', event => {
      const button = event.target.closest('button'); if (!button) return;
      const selector = button.classList.contains('sceneControl') ? '.sceneControl' : '.railControl';
      const index = Array.from(target.querySelectorAll(selector)).indexOf(button);
      if (index >= 0) source.querySelectorAll(selector)[index].click();
    });
  }, pointerSvg);
  const caption = (title, detail) => page.evaluate(({title, detail}) => {
    document.querySelector('#filmCaption').textContent = title;
    document.querySelector('#filmDetail').textContent = detail;
  }, {title, detail});
  const clickCue = async (locator, label, hold = 1400) => {
    await locator.scrollIntoViewIfNeeded();
    const box = await locator.boundingBox();
    if (!box) throw Error(`Missing click target: ${label}`);
    await page.evaluate(({box, label}) => {
      const pointer = document.querySelector('#filmPointer');
      const target = document.querySelector('#filmTarget');
      const text = document.querySelector('#filmTargetLabel');
      Object.assign(target.style, {display: 'block', left: `${box.x - 6}px`, top: `${box.y - 6}px`, width: `${box.width + 12}px`, height: `${box.height + 12}px`});
      Object.assign(pointer.style, {display: 'block', left: `${box.x + box.width / 2}px`, top: `${box.y + box.height / 2}px`});
      text.textContent = label;
      Object.assign(text.style, {display: 'block', left: `${Math.max(12, Math.min(box.x - 20, 1600 - 320))}px`, top: `${Math.max(110, box.y - 58)}px`});
    }, {box, label});
    await pause(hold);
    await locator.click();
    await pause(500);
    await page.evaluate(() => {for (const id of ['filmPointer', 'filmTarget', 'filmTargetLabel']) document.getElementById(id).style.display = 'none';});
  };
  await pause(2200);
  for (const label of ['Implementation', 'Review', 'Tests']) {
    await clickCue(page.getByRole('button', {name: `Connect ${label}`, exact: true}), `Connect ${label}`, 900);
    await page.getByRole('button', {name: `Disconnect ${label}`, exact: true}).waitFor();
    await pause(500);
  }
  await caption('Keep several sessions in view.', 'Each session has a color. The large symbol shows the selected session.');
  await pause(3000);
  await clickCue(page.getByRole('button', {name: 'Settings', exact: true}), 'Open settings', 800);
  await clickCue(page.getByRole('tab', {name: 'Devices', exact: true}), 'Devices', 600);
  await clickCue(page.getByRole('tab', {name: 'MIDI controllers', exact: true}), 'MIDI controllers', 600);
  await clickCue(page.getByRole('button', {name: 'Connect', exact: true}), 'Connect MIDI', 800);
  await clickCue(page.getByRole('button', {name: 'Back to pad', exact: true}), 'Back to the pad', 600);
  await page.evaluate(() => {document.querySelector('#controller').style.opacity = '1'; document.querySelector('#cable').classList.add('on');});
  await caption('Connect a Launchpad through USB MIDI.', 'The desktop pad and controller show the same session and available actions.');
  await pause(3000);
  await state('film-review', 'waiting_for_approval', 'Review');
  await approval();
  await page.getByRole('button', {name: 'Refresh chats', exact: true}).click();
  await caption('Select Review: right-side button 2.', 'Press the magenta round button, not a square inside the grid.');
  await pause(2600);
  await clickCue(page.locator('#controller .sceneControl').nth(1), '1. Select Review');
  await page.locator('.selectedConversation').getByRole('button', {name: 'Approve', exact: true}).waitFor();
  await pause(800);
  await page.screenshot({path: path.join(output, 'desktop-workflow-poster.png')});
  await caption('Approve: green button at the top left.', 'Read the request in Codex first. This approves only the selected request.');
  await pause(2600);
  await clickCue(page.locator('#controller .railControl').first(), '2. Approve');
  await pause(1800);
  if (!approved) throw Error('The controller approval did not reach the selected subscriber');
  await page.locator('.selectedConversation').getByRole('button', {name: 'Approve', exact: true}).waitFor({state: 'hidden'});
  await caption('That session continues. The others keep working.', 'Colors identify sessions; symbols show running, waiting, approval, and completion.');
  await pause(3200);
  await caption('No MIDI controller? Use the pad on screen.', 'Pad-Lattice also pairs with a phone or tablet on your local network.');
  await pause(3500);
  const video = page.video();
  await context.close();
  const source = await video.path();
  execFileSync('ffmpeg', ['-y', '-i', source, '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '22',
    '-pix_fmt', 'yuv420p', '-movflags', '+faststart', path.join(output, 'desktop-workflow.mp4')], {stdio: 'ignore'});
  console.log(`Created ${path.join(output, 'desktop-workflow.mp4')}`);
} finally {
  await browser?.close();
  for (const client of subscribers) client.destroy();
  server.close();
  engine.stdin.end();
  await new Promise(resolve => {if (engine.exitCode !== null) resolve(); else engine.once('exit', resolve);});
  for (const request of pending.values()) clearTimeout(request.timer);
}
