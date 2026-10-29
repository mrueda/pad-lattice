import {useEffect, useRef, useState} from 'react';
import {desktopRequest} from './desktop';

export interface Discovery {
  available: boolean;
  conversations: Array<{id: string; name: string; cwd: string; state: string;
    connected?: boolean; managed?: boolean; launcher?: boolean; error?: string; slot?: number | null; accent?: string}>;
  error?: string;
  truncated?: boolean;
}

// StrictMode remounts share an in-flight read, never a cached result.
let discovery: Promise<Discovery> | null = null;
function discover() {
  discovery ??= desktopRequest<Discovery>('list_conversations').finally(() => { discovery = null; });
  return discovery;
}

export function useConversationDiscovery(onLost: (id: string) => void) {
  const [result, setResult] = useState<Discovery | null>(null);
  const [busy, setBusy] = useState(false);
  const refresh = useRef<() => void>(() => {});
  const lostCallback = useRef(onLost);
  useEffect(() => {lostCallback.current = onLost;}, [onLost]);

  useEffect(() => {
    let disposed = false;
    let pending = false;
    let again = false;
    let cleanup: (() => void) | undefined;
    let refreshTimer: number | undefined;
    const load = async () => {
      if (disposed) return;
      if (pending) {again = true; return;}
      pending = true;
      setBusy(true);
      try {
        const next = await discover();
        if (!disposed) setResult(next);
      } catch (reason) {
        if (!disposed) setResult({available: false, conversations: [], error: String(reason)});
      } finally {
        pending = false;
        if (!disposed) setBusy(false);
        if (!disposed && again) {again = false; void load();}
      }
    };
    refresh.current = () => {void load();};
    void load();
    const onVisible = () => {if (!document.hidden) void load();};
    const timer = window.setInterval(onVisible, 10000);
    document.addEventListener('visibilitychange', onVisible);
    import('@tauri-apps/api/event').then(async ({listen}) => {
      if (disposed) return;
      const unlisten = await listen<{thread_id?: string}>('pad-lattice-attachment', ({payload}) => {
        if (disposed || !payload.thread_id) return;
        lostCallback.current(payload.thread_id);
        window.clearTimeout(refreshTimer);
        refreshTimer = window.setTimeout(() => {void load();}, 300);
      });
      if (disposed) unlisten(); else cleanup = unlisten;
    }).catch(() => {
      // Polling remains available when native event registration fails.
      if (!disposed) void load();
    });
    return () => {
      disposed = true;
      window.clearInterval(timer);
      window.clearTimeout(refreshTimer);
      document.removeEventListener('visibilitychange', onVisible);
      cleanup?.();
      refresh.current = () => {};
    };
  }, []);
  return {result, busy, refresh};
}
