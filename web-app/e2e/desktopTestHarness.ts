import type {Page} from '@playwright/test';

export async function desktopBridge(page: Page, request: (method: string, params: Record<string, unknown>) => unknown) {
  await page.exposeFunction('__desktopFixture', request);
  await page.addInitScript(() => {
    let id = 0;
    const callbacks = new Map<number, (event: unknown) => void>();
    const listeners = new Map<number, string>();
    Object.assign(window, {__emitSurface: (payload: unknown) => {
      for (const [handler, event] of listeners) if (event === 'pad-lattice-surface') callbacks.get(handler)?.({payload});
    }});
    Object.assign(window, {__TAURI_INTERNALS__: {
      transformCallback: (callback: (event: unknown) => void) => { callbacks.set(++id, callback); return id; },
      unregisterCallback: (handler: number) => callbacks.delete(handler),
      invoke: async (command: string, args: {method: string; params: Record<string, unknown>; handler: number; event: string; eventId: number}) => {
        if (command === 'plugin:event|listen') { listeners.set(args.handler, args.event); return args.handler; }
        if (command === 'plugin:event|unlisten') { listeners.delete(args.eventId); return; }
        return (window as unknown as {__desktopFixture: (method: string, params: object) => unknown})
          .__desktopFixture(command === 'desktop_request' ? args.method : command, command === 'desktop_request' ? args.params : args);
      },
    }});
  });
}

export async function emitSurface(page: Page, message: unknown) {
  await page.evaluate(payload => {
    (window as unknown as {__emitSurface: (message: unknown) => void}).__emitSurface(payload);
  }, message);
}
