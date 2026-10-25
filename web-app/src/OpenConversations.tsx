import {useEffect, useRef, useState} from 'react';
import {RefreshCw, Terminal, Plug, Unplug} from 'lucide-react';
import {desktopRequest} from './desktop';
import {tokenColor} from './surfaceModel';

interface Discovery {
  available: boolean;
  conversations: Array<{id: string; name: string; cwd: string; state: string;
    connected?: boolean; managed?: boolean; launcher?: boolean; error?: string; slot?: number | null; accent?: string}>;
  error?: string;
  truncated?: boolean;
}

const states: Record<string, string> = {
  idle: 'Idle', running: 'Working', approval: 'Approval needed',
  waiting: 'Waiting for reply', error: 'Error', unknown: 'Unknown',
};

let discovery: Promise<Discovery> | null = null;
function discover() {
  discovery ??= desktopRequest<Discovery>('list_conversations').finally(() => { discovery = null; });
  return discovery;
}

export function OpenConversations() {
  const [result, setResult] = useState<Discovery | null>(null);
  const [busy, setBusy] = useState(false);
  const [changing, setChanging] = useState<string | null>(null);
  const [error, setError] = useState('');
  const refresh = useRef<() => void>(() => {});
  useEffect(() => {
    let disposed = false;
    let pending = false;
    let again = false;
    const load = async () => {
      if (disposed) return;
      if (pending) { again = true; return; }
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
        if (!disposed && again) { again = false; void load(); }
      }
    };
    refresh.current = () => { void load(); };
    void load();
    const timer = window.setInterval(() => { if (!document.hidden) void load(); }, 10000);
    const onVisible = () => { if (!document.hidden) void load(); };
    document.addEventListener('visibilitychange', onVisible);
    return () => { disposed = true; window.clearInterval(timer); document.removeEventListener('visibilitychange', onVisible); };
  }, []);
  const connect = async (id: string, detach: boolean) => {
    setChanging(id); setError('');
    try {
      const next = await desktopRequest<{slot?: number}>(detach ? 'detach_conversation' : 'attach_conversation', {thread_id: id});
      if (!detach && next.slot != null) await desktopRequest('surface', {protocol: 1, type: 'select_session', slot: next.slot});
    } catch (reason) {
      setError(String(reason));
    } finally {
      setChanging(null);
      refresh.current();
    }
  };
  return <section className="openConversations" aria-label="Open Codex conversations" aria-busy={busy}>
    <div className="desktopToolbar">
      <h2>Open Codex conversations</h2>
      <button className="textButton" title="Refresh chats" aria-label="Refresh chats" disabled={busy} onClick={() => refresh.current()}><RefreshCw /></button>
    </div>
    {result?.error ? <p className="desktopNotice" role="status">{result.error}</p> : null}
    {error ? <p className="desktopError" role="alert">{error}</p> : null}
    {!result ? <p className="desktopNotice">Looking for local conversations...</p> : null}
    {result?.available && !result.conversations.length ? <p className="desktopNotice">No loaded Codex CLI conversations on this computer.</p> : null}
    {result?.conversations.length ? <ul className="openConversationList">
      {[...result.conversations].sort((a, b) =>
        (a.slot ?? Number.MAX_SAFE_INTEGER) - (b.slot ?? Number.MAX_SAFE_INTEGER)
        || a.name.localeCompare(b.name)).map((conversation) => <li key={conversation.id}>
        {conversation.slot != null ? <span className="openConversationScene" aria-label={`Scene ${conversation.slot + 1}`}
          style={conversation.accent ? {color: tokenColor(`accent:${conversation.accent}:selected`)} : undefined}>{conversation.slot + 1}</span>
          : <Terminal aria-hidden="true" />}
        <div className="openConversationIdentity"><strong title={conversation.name}>{conversation.name}</strong><span title={conversation.cwd}>{conversation.cwd || 'No working folder'}</span><code title={conversation.id}>{conversation.id.slice(0, 8)}</code></div>
        <div className="openConversationStatus"><span>{states[conversation.state] ?? 'Unknown'}</span><small>
          {conversation.error ? 'Disconnected' : conversation.connected || conversation.launcher
            ? `Connected${conversation.slot != null ? `, Scene ${conversation.slot + 1}` : ''}` : 'Not connected'}
        </small>{conversation.error ? <small className="desktopError" title={conversation.error}>{conversation.error}</small> : null}</div>
        {!conversation.launcher ? <button className="textButton" disabled={changing !== null}
          title={conversation.managed ? `Disconnect ${conversation.name}` : `Connect ${conversation.name}`}
          aria-label={conversation.managed ? `Disconnect ${conversation.name}` : `Connect ${conversation.name}`}
          onClick={() => void connect(conversation.id, Boolean(conversation.managed))}>
          {conversation.managed ? <Unplug /> : <Plug />}{conversation.managed ? 'Disconnect' : 'Connect'}
        </button> : null}
      </li>)}
    </ul> : null}
    {result?.truncated ? <p className="desktopNotice">Discovery limited to 64 loaded threads.</p> : null}
  </section>;
}
