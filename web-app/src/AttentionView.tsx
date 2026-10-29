import {useEffect, useState, type ReactNode} from 'react';
import {CircleAlert, CircleHelp, ShieldAlert, MessagesSquare, Bell, ArrowRight} from 'lucide-react';
import {desktopRequest} from './desktop';
import {tokenColor} from './surfaceModel';
import type {SessionView} from './types';

interface AttentionSnapshot {
  revision: number;
  sessions: Array<SessionView & {age_seconds: number; child_attention_count?: number}>;
  overflow_count: number;
}

export function elapsedLabel(seconds: number): string {
  const value = Math.max(0, Math.floor(seconds));
  if (value < 60) return `${value}s`;
  if (value < 3600) return `${Math.floor(value / 60)}m ${value % 60}s`;
  return `${Math.floor(value / 3600)}h ${Math.floor(value % 3600 / 60)}m`;
}

export function AttentionView({children, disabled, revision}: {
  children: ReactNode; disabled: boolean; revision: number | null | undefined;
}) {
  const [tab, setTab] = useState('all');
  const [snapshot, setSnapshot] = useState<AttentionSnapshot | null>(null);
  const [error, setError] = useState('');
  const [selecting, setSelecting] = useState(false);
  useEffect(() => {
    let disposed = false;
    let timer: number;
    setSnapshot(null);
    if (disabled) return;
    const refresh = async () => {
      try {
        const next = await desktopRequest<AttentionSnapshot>('attention');
        if (!disposed) { setSnapshot(next); setError(''); }
      } catch {
        if (!disposed) { setSnapshot(null); setError('Attention list unavailable. Reconnecting...'); }
      }
      if (!disposed) timer = window.setTimeout(() => void refresh(), 2000);
    };
    void refresh();
    return () => { disposed = true; clearTimeout(timer); };
  }, [disabled, revision]);
  const select = async (slot: number) => {
    if (!snapshot) return;
    setSelecting(true);
    try {
      // Keep the revision belonging to this list: a reused slot must not select another agent.
      await desktopRequest('surface', {protocol: 1, type: 'select_session', slot, expected_revision: snapshot.revision});
    } catch (reason) { setError(String(reason)); }
    finally { setSelecting(false); }
  };
  return <div className="attentionView">
    <div className="attentionTabs" role="tablist" aria-label="Conversation view" onKeyDown={event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const next = event.key === 'Home' ? 'all' : event.key === 'End' ? 'attention' : tab === 'all' ? 'attention' : 'all';
      setTab(next);
      document.getElementById(next === 'all' ? 'all-conversations-tab' : 'attention-tab')?.focus();
    }}>
      <button id="all-conversations-tab" role="tab" tabIndex={tab === 'all' ? 0 : -1} aria-controls="all-conversations-panel" aria-selected={tab === 'all'} onClick={() => setTab('all')}><MessagesSquare aria-hidden="true" /><span>All conversations</span></button>
      <button id="attention-tab" role="tab" tabIndex={tab === 'attention' ? 0 : -1} aria-controls="attention-panel" aria-selected={tab === 'attention'} onClick={() => setTab('attention')}>
        <Bell aria-hidden="true" /><span>Needs attention{snapshot ? ` (${snapshot.sessions.length})` : ''}</span></button>
    </div>
    {snapshot && snapshot.sessions.length > 0 ? <button className="textButton nextAttention" disabled={disabled || selecting || snapshot.revision !== revision}
      title="Select the next conversation that needs attention" onClick={() => {
        const index = snapshot.sessions.findIndex(session => session.selected);
        void select(snapshot.sessions[(index + 1) % snapshot.sessions.length].slot);
      }}><ArrowRight aria-hidden="true" />Next needing attention <span>{snapshot.sessions.length}</span></button> : null}
    <div id="all-conversations-panel" role="tabpanel" aria-labelledby="all-conversations-tab" hidden={tab !== 'all'}>{children}</div>
    <div id="attention-panel" role="tabpanel" aria-labelledby="attention-tab" hidden={tab !== 'attention'}>
      {error ? <p className="desktopError" role="status">{error}</p> : null}
      {!snapshot && !error ? <p className="desktopNotice">Checking conversations...</p> : null}
      {snapshot?.sessions.length === 0 ? <p className="desktopNotice">No conversations need attention</p> : null}
      <div className="attentionList">{snapshot?.sessions.map(session => {
        const Icon = session.state === 'waiting_for_approval' ? ShieldAlert : session.state === 'error' ? CircleAlert : CircleHelp;
        const label = session.state === 'waiting_for_approval' ? 'Approval needed' : session.state === 'error' ? 'Error' : 'Waiting for reply';
        return <button key={session.slot} className="attentionRow" disabled={disabled || selecting || snapshot.revision !== revision}
          aria-pressed={session.selected} title={`Select ${session.label}`} onClick={() => void select(session.slot)}>
          <i aria-hidden="true" style={{background: tokenColor(`accent:${session.accent}:selected`)}} />
          <span><strong>{session.label}</strong><small>Scene {session.slot + 1} · {label}</small>
            {session.child_attention_count ? <small>{session.child_attention_count} child agent{session.child_attention_count === 1 ? '' : 's'} need{session.child_attention_count === 1 ? 's' : ''} attention</small> : null}</span>
          <Icon aria-hidden="true" /><time aria-label={`In this state for ${elapsedLabel(session.age_seconds)}`}>{elapsedLabel(session.age_seconds)}</time>
        </button>;
      })}</div>
      {snapshot && snapshot.overflow_count > 0 ? <p className="desktopNotice">{snapshot.overflow_count} additional conversation(s) have no scene slot.</p> : null}
    </div>
  </div>;
}
