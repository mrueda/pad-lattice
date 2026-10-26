import {recordRequestFailure} from './diagnostics';

export const isDesktop = () => typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;

export async function desktopRequest<T>(method: string, params: object = {}): Promise<T> {
  const {invoke} = await import('@tauri-apps/api/core');
  try {return await invoke<T>('desktop_request', {method, params});}
  catch (error) {recordRequestFailure(method); throw error;}
}

export async function choosePath(): Promise<string | null> {
  const {invoke} = await import('@tauri-apps/api/core');
  return invoke<string | null>('choose_path');
}

export async function openProjectLink(destination: 'docs' | 'github'): Promise<void> {
  const {invoke} = await import('@tauri-apps/api/core');
  await invoke('open_project_link', {destination});
}

export interface SurfaceSocket {
  readyState: number;
  onopen: (() => void) | null;
  onmessage: ((event: {data: string}) => void) | null;
  onclose: (() => void) | null;
  onerror: (() => void) | null;
  send: (data: string) => void;
  close: () => void;
}

export function surfaceSocket(url: string): SurfaceSocket {
  if (!isDesktop()) {
    const socket = new WebSocket(url);
    const bridge: SurfaceSocket = {
      get readyState() { return socket.readyState; },
      onopen: null, onmessage: null, onclose: null, onerror: null,
      send: (data) => socket.send(data), close: () => socket.close(),
    };
    socket.onopen = () => bridge.onopen?.();
    socket.onmessage = (event) => bridge.onmessage?.({data: String(event.data)});
    socket.onclose = () => bridge.onclose?.();
    socket.onerror = () => bridge.onerror?.();
    return bridge;
  }
  let closed = false;
  const cleanup: Array<() => void> = [];
  const deliver = (message: unknown) => {
    if (!closed) bridge.onmessage?.({data: JSON.stringify(message)});
  };
  const bridge: SurfaceSocket = {
    readyState: 0, onopen: null, onmessage: null, onclose: null, onerror: null,
    send: (data) => {
      const message = JSON.parse(data) as {type: string};
      const work = message.type === 'authenticate'
        ? desktopRequest<{messages: unknown[]}>('snapshot').then(({messages}) => messages.forEach(deliver))
        : desktopRequest('surface', message);
      work.catch((error: unknown) => {
        deliver({protocol: 1, type: 'error', code: 'desktop_error', error: String(error)});
        if (message.type === 'authenticate' && !closed) {
          bridge.close();
          bridge.onclose?.();
        }
      });
    },
    close: () => { closed = true; bridge.readyState = 3; cleanup.splice(0).forEach((fn) => fn()); },
  };
  import('@tauri-apps/api/event').then(async ({listen}) => {
    const unlisten = await listen('pad-lattice-surface', ({payload}) => deliver(payload));
    if (closed) { unlisten(); return; }
    cleanup.push(unlisten);
    const disconnect = await listen('pad-lattice-disconnected', ({payload}) => {
      deliver({protocol: 1, type: 'error', error: String(payload)});
      bridge.close();
      bridge.onclose?.();
    });
    if (closed) { disconnect(); return; }
    cleanup.push(disconnect);
    bridge.readyState = 1;
    bridge.onopen?.();
  }).catch(() => bridge.onerror?.());
  return bridge;
}
