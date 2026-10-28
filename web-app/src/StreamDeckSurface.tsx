import {Check, Square, X, type LucideIcon} from 'lucide-react';
import {DemoPointer, type Demonstration} from './DemoPointer';
import {stateLabels} from './demo';
import {compileVisualFrame, tokenColor} from './surfaceModel';
import type {ControlAction, SessionView, SurfaceView} from './types';

interface Props {
  view: SurfaceView;
  disabled?: boolean;
  guidedAction?: ControlAction | null;
  guidedSlot?: number | null;
  demonstration?: Demonstration | null;
  onSelect: (slot: number) => void;
  onAction: (action: ControlAction) => void;
}

const actions: {action: 'approve' | 'reject' | 'stop'; label: string; Icon: LucideIcon}[] = [
  {action: 'approve', label: 'Approve', Icon: Check},
  {action: 'reject', label: 'Reject', Icon: X},
  {action: 'stop', label: 'Stop', Icon: Square},
];

function SessionGlyph({session}: {session: SessionView}) {
  const frame = compileVisualFrame({selected_state: session.state, sessions: [],
    available_actions: [], overflow_count: 0, activity_motion: false, frame: 0});
  return <svg className="deckGlyph" viewBox="0 0 70 80" aria-hidden="true">
    {frame.state.flatMap((row, y) => row.map((token, x) => token === 'off' ? null :
      <rect key={`${x}-${y}`} x={x * 10 + 1} y={y * 10 + 1} width="8" height="8" rx="1" fill={tokenColor(token)} />))}
  </svg>;
}

export function StreamDeckSurface({view, disabled = false, guidedAction, guidedSlot,
  demonstration, onSelect, onAction}: Props) {
  const selected = view.sessions.find(session => session.selected);
  const target = selected?.label ?? 'No session';
  return <div className="streamDeckSurface" aria-label="Stream Deck simulation">
    <div className="hardwareBrand"><span>elgato</span><strong>Stream Deck</strong></div>
    <div className="deckGroupLabel" id="deck-session-label">Sessions</div>
    <div className="deckSessionKeys" role="group" aria-labelledby="deck-session-label">
      {Array.from({length: 10}, (_, slot) => {
        if (slot >= 8) return <div key={slot} className="deckKey unusedDeckKey" aria-hidden="true" />;
        const session = view.sessions.find(item => item.slot === slot);
        return <button key={slot}
          className={`deckKey deckSessionKey ${session?.selected ? 'selected' : ''} ${guidedSlot === slot ? 'guidedControl' : ''}`}
          disabled={disabled || !session} aria-pressed={Boolean(session?.selected)}
          aria-label={session ? `Select ${session.label}` : `Empty Session ${slot + 1}`}
          title={session ? `${session.label}: ${stateLabels[session.state]}` : `Session ${slot + 1}: empty`}
          onClick={() => onSelect(slot)}>
          {session ? <>
            <span className="deckAccent" style={{background: tokenColor(`accent:${session.accent}:selected`)}} />
            <SessionGlyph session={session} />
            <span className="deckKeyLabel">{session.label}</span>
          </> : <span className="deckEmptyLabel">{slot + 1}</span>}
          {demonstration && guidedSlot === slot ? <DemoPointer {...demonstration} /> : null}
        </button>;
      })}
    </div>
    <div className="deckGroupLabel" id="deck-action-label">Actions <span>for {target}</span></div>
    <div className="deckActionKeys" role="group" aria-labelledby="deck-action-label">
      {actions.map(({action, label, Icon}) => {
        const available = Boolean(selected) && view.available_actions.includes(action);
        return <button key={action}
          className={`deckKey deckActionKey ${guidedAction === action ? 'guidedControl' : ''}`}
          disabled={disabled || !available} aria-label={label} title={`${label}: ${target}${available ? '' : ' (unavailable)'}`}
          style={{'--key-accent': available && selected ? tokenColor(`accent:${selected.accent}:selected`) : '#38444e',
            '--action-color': available ? tokenColor(`action:${action}:enabled`) : '#657079'} as React.CSSProperties}
          onClick={() => onAction(action)}>
          <Icon className="deckActionIcon" aria-hidden="true" />
          <span className="deckActionLabel">{label}</span>
          <span className="deckKeyLabel">{target}</span>
          {demonstration && guidedAction === action ? <DemoPointer {...demonstration} /> : null}
        </button>;
      })}
      <div className="deckKey unusedDeckKey" aria-hidden="true" />
      <div className="deckKey unusedDeckKey" aria-hidden="true" />
    </div>
  </div>;
}
