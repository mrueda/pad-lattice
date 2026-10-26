import WebSocket from 'ws';
import {isAccentName, isAgentState} from '../../../web-app/src/surfaceModel';
import {controlActions, type SurfaceView} from '../../../web-app/src/types';

export type LiveView = SurfaceView & {control_revision: number};
export type ActionName = 'approve' | 'reject' | 'stop';

// Credentials must never be sent to arbitrary hosts or appear in URLs/logs.
export function bridgeOrigin(value: string): string {
  const url = new URL(value);
  const host = url.hostname;
  const parts = host.split('.').map(Number);
  const privateV4 = parts.length === 4 && parts.every(n => Number.isInteger(n) && n >= 0 && n <= 255)
    && (parts[0] === 10 || (parts[0] === 192 && parts[1] === 168)
      || (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31));
  if (url.protocol !== 'http:' || (!privateV4 && host !== '127.0.0.1' && host !== 'localhost')
    || url.username || url.password || url.hash || url.search || url.pathname !== '/') {
    throw new Error('Use an HTTP address on localhost or a private IPv4 network, without a path or credential.');
  }
  return url.origin;
}

export function liveView(value: unknown): LiveView | null {
  if (!value || typeof value !== 'object') return null;
  const v = value as LiveView;
  if (!Number.isSafeInteger(v.control_revision) || v.control_revision < 0
    || !Array.isArray(v.sessions) || v.sessions.length > 8
    || !Array.isArray(v.available_actions) || !v.available_actions.every(a => controlActions.includes(a))) return null;
  const slots = new Set<number>();
  for (const s of v.sessions) {
    if (!s || !Number.isInteger(s.slot) || s.slot < 0 || s.slot > 7 || slots.has(s.slot)
      || !isAgentState(s.state) || !isAccentName(s.accent) || typeof s.selected !== 'boolean'
      || typeof s.label !== 'string' || s.label.length > 80) return null;
    slots.add(s.slot);
  }
  if (v.sessions.filter(s => s.selected).length > 1) return null;
  return v;
}

export class Bridge {
  view: LiveView | null = null;
  status = 'Pair device';
  private socket: WebSocket | null = null;
  private token: string | null = null;
  private origin = '';
  private authenticated = false;
  private stopped = true;
  private retry: ReturnType<typeof setTimeout> | undefined;
  private watchdog: ReturnType<typeof setTimeout> | undefined;
  private heartbeat: ReturnType<typeof setInterval> | undefined;
  private retryDelay = 1000;
  constructor(private changed: () => void) {}

  pair(address: string, pin: string) {
    const origin = bridgeOrigin(address);
    if (!/^\d{6}$/.test(pin)) throw new Error('Enter a fresh six-digit pairing PIN.');
    this.disconnect();
    this.origin = origin;
    this.token = pin;
    this.stopped = false;
    this.open();
  }

  disconnect() {
    this.stopped = true;
    clearTimeout(this.retry);
    clearTimeout(this.watchdog);
    clearInterval(this.heartbeat);
    const previous = this.socket;
    this.socket = null;
    previous?.terminate();
    this.token = null;
    this.authenticated = false;
    this.view = null;
    this.status = 'Pair device';
    this.changed();
  }

  select(slot: number, expected: number): boolean {
    if (!this.view?.sessions.some(s => s.slot === slot)) return false;
    return this.send({type: 'select_session', slot}, expected);
  }

  act(action: ActionName, expected: number): boolean {
    if (!this.view?.sessions.some(s => s.selected) || !this.view.available_actions.includes(action)) return false;
    return this.send({type: 'action', action}, expected);
  }

  private send(command: object, expected: number): boolean {
    if (!this.authenticated || !this.view || this.view.control_revision !== expected
      || this.socket?.readyState !== WebSocket.OPEN) return false;
    this.socket.send(JSON.stringify({protocol: 1, ...command, expected_revision: expected}));
    // A second key press must wait for a new authoritative surface snapshot.
    this.view = null;
    this.changed();
    return true;
  }

  private open() {
    if (this.stopped || !this.token) return;
    this.status = 'Connecting';
    this.changed();
    const socket = new WebSocket(this.origin.replace('http:', 'ws:') + '/ws', {
      origin: this.origin, maxPayload: 16384, followRedirects: false, handshakeTimeout: 5000,
      headers: {'User-Agent': 'pad-lattice-stream-deck'},
    });
    this.socket = socket;
    this.watchdog = setTimeout(() => socket.terminate(), 10000);
    socket.on('open', () => socket.send(JSON.stringify({protocol: 1, type: 'authenticate', credential: this.token})));
    socket.on('message', raw => {
      if (this.socket !== socket) return;
      let m;
      try { m = JSON.parse(raw.toString()); } catch { socket.terminate(); return; }
      if (!m || typeof m !== 'object' || m.protocol !== 1) { socket.terminate(); return; }
      if (m.type === 'authenticated') {
        // This plugin deliberately refuses administrator credentials.
        if (m.admin || (m.session_token !== null && typeof m.session_token !== 'string')) {
          this.disconnect(); return;
        }
        if (m.session_token) this.token = m.session_token;
        this.authenticated = true;
        clearTimeout(this.watchdog);
        this.heartbeat = setInterval(() => {
          this.watchdog = setTimeout(() => socket.terminate(), 5000);
          socket.ping();
        }, 10000);
        this.retryDelay = 1000;
        this.status = 'Connected';
      } else if (m.type === 'device_disconnected') {
        this.stopped = true;
        this.view = null;
        this.status = 'Disconnected';
      } else if (m.type === 'surface' && this.authenticated) {
        this.view = m.visual_protocol === 1 ? liveView(m.view) : null;
        this.status = this.view ? 'Connected' : 'No live session';
      } else if (m.type === 'error') {
        if (['forbidden', 'authentication_timeout'].includes(m.code)) {
          this.disconnect(); return;
        }
        this.view = null;
        this.status = 'Action unavailable';
      }
      this.changed();
    });
    socket.on('error', () => { /* Close handles state without logging credentials. */ });
    socket.on('pong', () => { if (this.socket === socket) clearTimeout(this.watchdog); });
    socket.on('close', code => {
      if (this.socket !== socket) return;
      clearTimeout(this.watchdog);
      clearInterval(this.heartbeat);
      this.socket = null;
      this.authenticated = false;
      this.view = null;
      if (code === 1008) { this.disconnect(); return; }
      this.status = 'Disconnected';
      this.changed();
      if (!this.stopped) {
        this.retry = setTimeout(() => this.open(), this.retryDelay);
        this.retryDelay = Math.min(this.retryDelay * 2, 15000);
      }
    });
  }
}
