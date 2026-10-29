import type {ReactNode} from 'react';
import {Check, X, Square, RefreshCw, ShieldAlert, CircleHelp, CircleAlert, MonitorSmartphone} from 'lucide-react';
import {stateLabels} from './demo';
import {tokenColor, isAgentState} from './surfaceModel';
import type {AgentState, ControlAction, SessionView, SurfaceView} from './types';

export function SelectedConversation({view, disabled, onAction, children}: {view: SurfaceView; disabled: boolean; onAction: (action: ControlAction) => void; children?: ReactNode}) {
  const selected = view.sessions.find(session => session.selected);
  const actions = [
    {action: 'approve' as const, label: 'Approve', Icon: Check},
    {action: 'reject' as const, label: 'Reject', Icon: X},
    {action: 'stop' as const, label: 'Stop', Icon: Square},
    {action: 'retry' as const, label: 'Retry', Icon: RefreshCw},
  ];
  return <section className={`selectedConversation${selected ? ' hasSelection' : ''}`} aria-label="Selected Codex conversation" aria-live="polite"
    style={selected ? {'--session-accent': tokenColor(`accent:${selected.accent}:selected`)} as React.CSSProperties : undefined}>
    <div className="sectionTitle"><span>SELECTED CONVERSATION</span>{selected ? <span>Scene {selected.slot + 1}</span> : null}</div>
    {selected ? <>
      <h2><i aria-hidden="true" style={{backgroundColor: tokenColor(`accent:${selected.accent}:selected`)}} />{selected.label}</h2>
      <SessionState state={selected.state} />
      {children}
      <div className="conversationActions">
        {actions.filter(({action}) => view.available_actions.includes(action)).map(({action, label, Icon}) =>
          <button key={action} disabled={disabled} className={`textButton action-${action}`} onClick={() => onAction(action)}><Icon />{label}</button>)}
      </div>
    </> : <h2>{view.sessions.length ? 'No conversation selected' : 'No Codex conversation connected'}</h2>}
  </section>;
}

const attentionIcons = {waiting_for_approval: ShieldAlert, waiting_for_reply: CircleHelp, error: CircleAlert};

function SessionState({state}: {state: AgentState}) {
  const Icon = state in attentionIcons ? attentionIcons[state as keyof typeof attentionIcons] : null;
  return <span className={`stateLabel ${Icon ? `attentionState ${state}` : ''}`}>
    {Icon ? <Icon aria-hidden="true" /> : null}{stateLabels[state]}
  </span>;
}

export function SessionList({
  sessions,
  title = 'AGENT SCENES',
  sandbox = false,
  readOnly = false,
  guidedSlot = null,
  onSelect,
  onState,
}: {
  sessions: SessionView[];
  title?: string;
  sandbox?: boolean;
  readOnly?: boolean;
  guidedSlot?: number | null;
  onSelect: (slot: number) => void;
  onState?: (slot: number, state: AgentState) => void;
}) {
  return (
    <section className="sessionSection">
      <div className="sectionTitle"><span>{title}</span><span>{sessions.length}/8</span></div>
      <div className="sessionList">
        {sessions.map((session) => (
          <div
            className={`sessionRow ${session.selected ? 'selected' : ''} ${guidedSlot === session.slot ? 'guidedRow' : ''}`}
            style={{'--session-accent': tokenColor(`accent:${session.accent}:selected`)} as React.CSSProperties}
            key={session.slot}>
            <button disabled={readOnly} onClick={() => onSelect(session.slot)} title={`Select ${session.label}`} aria-pressed={session.selected}>
              <i aria-hidden="true" style={{backgroundColor: tokenColor(`accent:${session.accent}:selected`)}} />
              <span><strong>{session.label}</strong><small>Scene {session.slot + 1}</small></span>
            </button>
            {sandbox && onState ? (
              <select
                aria-label={`${session.label} state`}
                onChange={(event) => isAgentState(event.target.value) && onState(session.slot, event.target.value)}
                value={session.state}>
                {Object.entries(stateLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            ) : (
              <SessionState state={session.state} />
            )}
          </div>
        ))}
        {sessions.length === 0 ? (
          <div className="emptySessions">
            <MonitorSmartphone aria-hidden="true" />
            <span><strong>No active agents</strong><small>Codex sessions will appear here.</small></span>
          </div>
        ) : null}
      </div>
    </section>
  );
}
