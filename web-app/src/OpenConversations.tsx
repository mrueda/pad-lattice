import {useEffect, useRef, useState} from 'react';
import {RefreshCw, Terminal, Plug, Unplug, Stethoscope, Settings, ChevronDown, Trash2, RotateCcw} from 'lucide-react';
import {desktopRequest} from './desktop';
import {tokenColor} from './surfaceModel';
import {useConversationDiscovery, type Discovery} from './useConversationDiscovery';

const states: Record<string, string> = {
  idle: 'Ready', running: 'Working', approval: 'Approval needed',
  waiting: 'Waiting for reply', error: 'Error', unknown: 'Unknown',
};

export function OpenConversations({onSetup, onDiagnostics, codexAvailable}: {
  onSetup: () => void; onDiagnostics: () => void; codexAvailable?: boolean;
}) {
  const [changing, setChanging] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState<boolean | null>(null);
  const [lost, setLost] = useState<string[]>([]);
  const [removed, setRemoved] = useState<string[]>(() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem('pad-lattice-removed-chats') ?? '[]');
      return Array.isArray(saved) ? saved.filter(id => typeof id === 'string').slice(-128) : [];
    } catch { return []; }
  });
  const [removing, setRemoving] = useState<Discovery['conversations'][number] | null>(null);
  const removeDialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (removing) removeDialog.current?.showModal(); else removeDialog.current?.close();
  }, [removing]);
  useEffect(() => {
    try {sessionStorage.setItem('pad-lattice-removed-chats', JSON.stringify(removed));} catch { /* Memory-only fallback. */ }
  }, [removed]);
  const {result, busy, refresh} = useConversationDiscovery(id => {
    setLost(previous => [...new Set([...previous, id])]);
    setExpanded(true);
  });
  const visible = result?.conversations.filter(c => !removed.includes(c.id)) ?? [];
  const picker = useRef<HTMLButtonElement>(null);
  const connectedCount = result?.conversations.filter(c => !c.error && (c.connected || c.launcher)).length ?? 0;
  const open = expanded ?? connectedCount === 0;
  const connect = async (id: string, detach: boolean) => {
    setExpanded(true);
    setChanging(id); setError('');
    try {
      const next = await desktopRequest<{slot?: number}>(detach ? 'detach_conversation' : 'attach_conversation', {thread_id: id});
      if (!detach && next.slot != null) await desktopRequest('surface', {protocol: 1, type: 'select_session', slot: next.slot});
      if (!detach) setLost(previous => previous.filter(thread => thread !== id));
    } catch (reason) {
      setError(String(reason));
    } finally {
      setChanging(null);
      refresh.current();
    }
  };
  return <section className="openConversations" aria-label="Codex conversations" aria-busy={busy}
    onKeyDown={event => {
      if (event.key === 'Escape' && open) {event.preventDefault(); setExpanded(false); picker.current?.focus();}
    }}>
    <div className="desktopToolbar">
      <h2><button ref={picker} className="conversationPicker" aria-expanded={open} aria-controls="conversation-picker-list"
        onClick={() => setExpanded(!open)}>
        <Terminal aria-hidden="true" /><span>Codex conversations</span>
        {result ? <span className="conversationCounts" role="status">{visible.length} available · {connectedCount} on pad</span> : null}
        <ChevronDown aria-hidden="true" className="pickerChevron" />
      </button></h2>
      <button className="textButton" title="Refresh chats" aria-label="Refresh chats" disabled={busy} onClick={() => refresh.current()}><RefreshCw /></button>
      {removed.length ? <button className="textButton" title="Restore removed conversations" aria-label="Restore removed conversations"
        onClick={() => {setRemoved([]); refresh.current();}}><RotateCcw /></button> : null}
    </div>
    {result?.error ? <p className="desktopNotice" role="status">{result.error}</p> : null}
    {lost.length ? <p className="desktopNotice" role="status">A Codex connection was lost. Refresh chats and reconnect if it is still open.
      <button className="textButton" onClick={() => setLost([])}>Dismiss</button></p> : null}
    {error ? <p className="desktopError" role="alert">{error}</p> : null}
    {result?.error || error ? <button className="textButton" onClick={onDiagnostics}><Stethoscope /> Diagnostics</button> : null}
    {!result ? <p className="desktopNotice">Looking for local conversations...</p> : null}
    <div id="conversation-picker-list" hidden={!open}>
    {result && !visible.length ? <div className="conversationEmpty">
      <Terminal aria-hidden="true" />
      <strong>{codexAvailable === false ? 'Codex CLI not available' : result.available ? 'No available Codex conversations' : 'Codex discovery unavailable'}</strong>
      {result.available && codexAvailable !== false ? <code>codex</code> : <button className="textButton" onClick={onSetup}><Settings aria-hidden="true" />Codex settings</button>}
    </div> : null}
    {visible.length ? <ul className="openConversationList">
      {[...visible].sort((a, b) =>
        (a.slot ?? Number.MAX_SAFE_INTEGER) - (b.slot ?? Number.MAX_SAFE_INTEGER)
        || a.name.localeCompare(b.name)).map((conversation) => <li key={conversation.id}>
        {conversation.slot != null ? <span className="openConversationScene" aria-label={`Scene ${conversation.slot + 1}`}
          style={conversation.accent ? {color: tokenColor(`accent:${conversation.accent}:selected`)} : undefined}>{conversation.slot + 1}</span>
          : <Terminal aria-hidden="true" />}
        <div className="openConversationIdentity"><strong title={conversation.name}>{conversation.name}</strong><span title={conversation.cwd}>{conversation.cwd || 'No working folder'}</span><code title={conversation.id}>{conversation.id.slice(0, 8)}</code></div>
        <div className="openConversationStatus"><span>{states[conversation.state] ?? 'Unknown'}</span><small
          className={!conversation.error && (conversation.connected || conversation.launcher) ? 'chatConnected' : undefined}>
          {conversation.error ? 'Disconnected' : conversation.connected || conversation.launcher
            ? `On pad${conversation.slot != null ? `, Scene ${conversation.slot + 1}` : ''}` : 'Not connected'}
        </small>{conversation.error ? <small className="desktopError" title={conversation.error}>{conversation.error}</small> : null}</div>
        {!conversation.launcher ? <button className="textButton" disabled={changing !== null}
          title={conversation.managed ? `Disconnect ${conversation.name}` : `${lost.includes(conversation.id) ? 'Reconnect' : 'Connect'} ${conversation.name}`}
          aria-label={conversation.managed ? `Disconnect ${conversation.name}` : `${lost.includes(conversation.id) ? 'Reconnect' : 'Connect'} ${conversation.name}`}
          onClick={() => void connect(conversation.id, Boolean(conversation.managed))}>
          {conversation.managed ? <Unplug /> : <Plug />}{conversation.managed ? 'Disconnect' : lost.includes(conversation.id) ? 'Reconnect' : 'Connect'}
        </button> : null}
        {!conversation.launcher ? <button className="textButton removeConversation" disabled={changing !== null}
          title={`Remove ${conversation.name} from Pad-Lattice`} aria-label={`Remove ${conversation.name} from Pad-Lattice`}
          onClick={() => {setError(''); setRemoving(conversation);}}><Trash2 /></button> : null}
      </li>)}
    </ul> : null}
    {result?.truncated ? <p className="desktopNotice">Discovery limited to 64 loaded threads.</p> : null}
    </div>
    <dialog className="pairingDialog" ref={removeDialog} aria-labelledby="remove-conversation-title"
      onCancel={() => setRemoving(null)} onKeyDown={event => event.stopPropagation()}>
      <h2 id="remove-conversation-title">Remove from Pad-Lattice?</h2>
      <p>{removing?.name}</p>
      <p>This disconnects the pad link and hides the entry. Codex history is not deleted and its work is not stopped.</p>
      <div className="desktopActions">
        <button className="textButton" disabled={changing !== null} onClick={() => setRemoving(null)}>Cancel</button>
        <button className="textButton danger" disabled={changing !== null} onClick={async () => {
          if (!removing) return;
          setChanging(removing.id);
          try {
            await desktopRequest('detach_conversation', {thread_id: removing.id});
            setRemoved(previous => [...new Set([...previous, removing.id])].slice(-128));
            setRemoving(null); refresh.current();
          } catch (reason) {setError(String(reason)); setRemoving(null);}
          finally {setChanging(null);}
        }}><Trash2 /> Remove</button>
      </div>
    </dialog>
  </section>;
}
