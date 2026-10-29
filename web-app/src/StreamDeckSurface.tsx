import {useEffect, useState} from 'react';
import {Check, ChevronLeft, ChevronRight, RotateCcw, Square, X, type LucideIcon} from 'lucide-react';
import {DemoPointer, type Demonstration} from './DemoPointer';
import {stateLabels} from './demo';
import {compileVisualFrame, tokenColor} from './surfaceModel';
import {deckShowColors} from './deckShow';
import layouts from '../../integrations/stream-deck/layouts.json';
import type {ControlAction, FullSurfaceFrame, SessionView, SurfaceView} from './types';

export const deckModel = (surface: string) => surface === 'stream-deck-xl' ? 'xl' : surface === 'stream-deck-neo' ? 'neo' : 'standard';

interface Props {
  view: SurfaceView;
  disabled?: boolean;
  guidedAction?: ControlAction | null;
  guidedSlot?: number | null;
  demonstration?: Demonstration | null;
  live?: boolean;
  includeRetry?: boolean;
  model?: keyof typeof layouts;
  showMode?: boolean;
  performanceFrame?: FullSurfaceFrame | null;
  performanceAct?: string | null;
  performanceCaption?: string | null;
  onSelect: (slot: number) => void;
  onAction: (action: ControlAction) => void;
}

const actions: {action: ControlAction; label: string; Icon: LucideIcon}[] = [
  {action: 'approve', label: 'Approve', Icon: Check},
  {action: 'reject', label: 'Reject', Icon: X},
  {action: 'stop', label: 'Stop', Icon: Square},
  {action: 'retry', label: 'Retry', Icon: RotateCcw},
];
const attentionStates = new Set(['waiting_for_approval', 'waiting_for_reply', 'error']);

function SessionGlyph({session}: {session: SessionView}) {
  const frame = compileVisualFrame({selected_state: session.state, sessions: [],
    available_actions: [], overflow_count: 0, activity_motion: false, frame: 0});
  return <svg className="deckGlyph" viewBox="0 0 70 80" aria-hidden="true">
    {frame.state.flatMap((row, y) => row.map((token, x) => token === 'off' ? null :
      <rect key={`${x}-${y}`} x={x * 10 + 1} y={y * 10 + 1} width="8" height="8" rx="1" fill={tokenColor(token)} />))}
  </svg>;
}

export function StreamDeckSurface({view, disabled = false, guidedAction, guidedSlot,
  demonstration, live = false, includeRetry = false, model = 'standard', showMode = false, performanceFrame = null,
  performanceAct, performanceCaption, onSelect, onAction}: Props) {
  const selected = view.sessions.find(session => session.selected);
  const target = selected?.label ?? 'No session';
  const layout = layouts[model];
  const [page, setPage] = useState(() => model === 'neo' && (selected?.slot ?? 0) >= 5 ? 1 : 0);
  useEffect(() => {setPage(model === 'neo' && (selected?.slot ?? 0) >= 5 ? 1 : 0);}, [model, selected?.slot]);
  useEffect(() => {if (model === 'neo' && guidedSlot != null) setPage(guidedSlot >= 5 ? 1 : 0);}, [model, guidedSlot]);
  const currentPage = Math.min(page, layout.pages.length - 1);
  const slots = layout.pages[currentPage];
  const attentionOnPage = (index: number) => {
    if (live && disabled) return 0;
    const pageSlots = layout.pages[index];
    return pageSlots ? view.sessions.filter(session => pageSlots.includes(session.slot) && attentionStates.has(session.state)).length : 0;
  };
  const previousAttention = currentPage > 0 ? attentionOnPage(currentPage - 1) : 0;
  const nextAttention = currentPage < layout.pages.length - 1 ? attentionOnPage(currentPage + 1) : 0;
  const pageLabel = (direction: 'Previous' | 'Next', pageNumber: number, count: number) => count
    ? `${direction} page, page ${pageNumber}: ${count} ${count === 1 ? 'conversation needs' : 'conversations need'} attention`
    : `${direction} page`;
  return <div className={`streamDeckSurface deckLayout-${model}`} aria-label={live ? 'Stream Deck-style control surface' : 'Stream Deck simulation'}
    style={{'--deck-columns': layout.columns} as React.CSSProperties}>
    <div className="hardwareBrand"><span>{live ? 'PAD-LATTICE' : 'elgato'}</span><strong>{layout.label}{live ? '-style' : ''}</strong></div>
    {showMode ? <>
      <div className="performanceStory"><span>{performanceAct ?? 'VISUAL SHOW'}</span><strong>{performanceCaption ?? 'Ready'}</strong></div>
      <div className="deckShowKeys" role="img" aria-label={`Visual Show animation on ${layout.columns * layout.rows} keys`}>
        {deckShowColors(performanceFrame, layout.columns, layout.rows).map((color, index) => <span key={index} className="deckShowKey"
          style={{'--pad-color': color} as React.CSSProperties} />)}
      </div>
    </> : <>
    <div className="deckGroupLabel"><span>Sessions and actions</span><span>Selected: {target}</span></div>
    <div className="deckGrid" role="group" aria-label="Session and action keys">
      {slots.map((slot, index) => {
        if (slot === null || slot === 'retry' && !includeRetry) return <div key={index} className="deckKey unusedDeckKey" aria-hidden="true" />;
        if (typeof slot === 'number') {
        const session = view.sessions.find(item => item.slot === slot);
        return <button key={index}
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
        }
        const item = actions.find(action => action.action === slot);
        if (!item) return null;
        const {action, label, Icon} = item;
        const available = Boolean(selected) && view.available_actions.includes(action);
        return <button key={index}
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
    </div>
    {layout.pages.length > 1 ? <div className="deckPages" aria-label="Stream Deck pages">
      <button className="textButton" aria-label={pageLabel('Previous', currentPage, previousAttention)} title={pageLabel('Previous', currentPage, previousAttention)}
        disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}><ChevronLeft />
        {previousAttention > 0 ? <span className="deckPageAttention" aria-hidden="true">{previousAttention}</span> : null}</button>
      <span>Page {currentPage + 1} / {layout.pages.length}</span>
      <button className="textButton" aria-label={pageLabel('Next', currentPage + 2, nextAttention)} title={pageLabel('Next', currentPage + 2, nextAttention)}
        disabled={currentPage >= layout.pages.length - 1} onClick={() => setPage(currentPage + 1)}><ChevronRight />
        {nextAttention > 0 ? <span className="deckPageAttention" aria-hidden="true">{nextAttention}</span> : null}</button>
      <span className="deckPageStatus" role="status">{previousAttention || nextAttention
        ? `Page ${previousAttention ? currentPage : currentPage + 2}: ${previousAttention || nextAttention} ${(previousAttention || nextAttention) === 1 ? 'conversation needs' : 'conversations need'} attention`
        : ''}</span>
    </div> : null}
    {live && model === 'neo' && selected && view.available_actions.includes('retry') ? <div className="deckExtraAction">
      <button className="textButton" disabled={disabled} aria-label={`Retry ${selected.label}`} title={`Retry ${selected.label}`}
        onClick={() => onAction('retry')}><RotateCcw aria-hidden="true" /> Retry</button>
    </div> : null}
    </>}
  </div>;
}
