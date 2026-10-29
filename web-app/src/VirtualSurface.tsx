import {
  Check,
  MoreHorizontal,
  RotateCcw,
  Square,
  X,
  type LucideIcon,
} from 'lucide-react';
import {tokenColor} from './surfaceModel';
import {DemoPointer, type Demonstration} from './DemoPointer';
import type {ControlAction, FullSurfaceFrame, SurfaceView, VisualFrame} from './types';

interface Props {
  variant?: 'virtual' | 'launchpad';
  frame: VisualFrame;
  performanceFrame?: FullSurfaceFrame | null;
  showMode?: boolean;
  performanceAct?: string | null;
  performanceCaption?: string | null;
  guidedAction?: ControlAction | null;
  guidedSlot?: number | null;
  demonstration?: Demonstration | null;
  view: SurfaceView;
  disabled?: boolean;
  onAction: (action: ControlAction) => void;
  onSelect: (slot: number) => void;
}

interface TopControl {
  action?: ControlAction;
  system?: 'overflow';
  label: string;
  icon?: LucideIcon;
}

const topControls: TopControl[] = [
  {action: 'approve', label: 'Approve', icon: Check},
  {action: 'reject', label: 'Reject', icon: X},
  {label: 'Reserved'},
  {label: 'Reserved'},
  {system: 'overflow', label: 'Session overflow', icon: MoreHorizontal},
  {label: 'Reserved'},
  {action: 'retry', label: 'Retry', icon: RotateCcw},
  {action: 'stop', label: 'Stop', icon: Square},
];

export function VirtualSurface({
  variant = 'virtual',
  frame,
  performanceFrame = null,
  showMode = false,
  performanceAct = null,
  performanceCaption = null,
  guidedAction = null,
  guidedSlot = null,
  demonstration = null,
  view,
  disabled = false,
  onAction,
  onSelect,
}: Props) {
  const performance = showMode || performanceFrame !== null;
  const launchpad = variant === 'launchpad';
  const selected = performance ? undefined : view.sessions.find(session => session.selected);
  return (
    <div
      className={`virtualSurface ${launchpad ? 'launchpadSurface' : ''} ${performance ? 'performanceSurface' : ''}`}
      style={selected ? {'--session-accent': tokenColor(`accent:${selected.accent}:selected`)} as React.CSSProperties : undefined}
      aria-label={launchpad ? 'Launchpad Pro Mk1 simulation' : 'Pad-Lattice virtual control surface'}>
      {launchpad ? <div className="hardwareBrand"><span>novation</span><strong>Launchpad Pro Mk1</strong></div> : null}
      {performance ? (
        <div className="performanceStory">
          <span>{performanceAct ?? 'VISUAL SHOW'}</span>
          <strong>{performanceCaption ?? 'The story continues'}</strong>
        </div>
      ) : (
        <div className="surfaceCaption">
          <span>ACTIONS</span>
          <span>VISUAL PROTOCOL 1</span>
        </div>
      )}
      <div className="surfaceTop">
        {launchpad ? <span aria-hidden="true" /> : null}
        <div className="topRail">
          {topControls.map((control, index) => {
            const token = control.action
              ? frame.actions[control.action]
              : control.system === 'overflow'
                ? frame.overflow
                : 'off';
            const displayColor = performanceFrame?.top[index] ?? tokenColor(token);
            const enabled = !performance && !disabled && token !== 'off' && Boolean(control.action);
            const Icon = control.icon;
            return (
              <button
                className={`railControl ${token !== 'off' && !performance ? 'litControl' : ''} ${guidedAction === control.action ? 'guidedControl' : ''}`}
                disabled={!enabled}
                key={index}
                onClick={() => control.action && onAction(control.action)}
                style={{'--pad-color': displayColor} as React.CSSProperties}
                title={performance ? `Show top light ${index + 1}` : control.label}
                aria-label={performance ? `Show top light ${index + 1}` : control.label}>
                {!performance && Icon ? <Icon aria-hidden="true" className={token === 'off' ? 'inactiveActionIcon' : undefined} /> : null}
                {demonstration && guidedAction === control.action ? <DemoPointer {...demonstration} /> : null}
              </button>
            );
          })}
        </div>
        <span aria-hidden="true" />
      </div>

      <div className="surfaceBody">
        {launchpad ? <div className="reservedRail" aria-label="Reserved left buttons">
          {Array.from({length: 8}, (_, index) => <span key={index} title="Reserved" />)}
        </div> : null}
        <div className="matrixGrid" aria-label={performance ? 'Visual Show light grid' : 'Selected-agent state and agent status grid'}>
          {Array.from({length: 8}, (_, row) =>
            Array.from({length: 8}, (_, column) => {
              const token = column === 7 ? frame.statuses[row] : frame.state[row][column];
              const status = !performance && column === 7;
              const statusSession = status
                ? view.sessions.find((session) => session.slot === row)
                : undefined;
              return (
                <span
                  className={`matrixPad ${status ? 'statusPad' : ''} ${token !== 'off' && !performance ? 'litPad' : ''}`}
                  key={`${row}-${column}`}
                  style={{
                    '--pad-color': performanceFrame?.grid[row]?.[column] ?? tokenColor(token),
                  } as React.CSSProperties}
                  title={statusSession ? `${statusSession.label}: ${statusSession.state}` : undefined}
                />
              );
            }),
          )}
        </div>
        <div className="sceneRail" aria-label={performance ? 'Show right lights' : 'Agent Scenes'}>
          {frame.selectors.map((token, slot) => {
            const session = view.sessions.find((item) => item.slot === slot);
            return (
              <button
                className={`sceneControl ${token !== 'off' && !performance ? 'litControl' : ''} ${guidedSlot === slot ? 'guidedControl' : ''}`}
                disabled={performance || disabled || token === 'off'}
                key={slot}
                onClick={() => onSelect(slot)}
                style={{
                  '--pad-color': performanceFrame?.right[slot] ?? tokenColor(token),
                } as React.CSSProperties}
                title={performance ? `Show right light ${slot + 1}` : session ? `Select ${session.label}` : `Empty Scene ${slot + 1}`}
                aria-pressed={!performance && Boolean(session?.selected)}
                aria-label={performance ? `Show right light ${slot + 1}` : session ? `Select ${session.label}` : `Empty Scene ${slot + 1}`}>
                <span>{!performance && session ? slot + 1 : ''}</span>
                {demonstration && guidedSlot === slot ? <DemoPointer {...demonstration} /> : null}
              </button>
            );
          })}
        </div>
      </div>
      {launchpad ? <div className="launchpadBottom" aria-label="Reserved bottom buttons">
        <span aria-hidden="true" />
        <div className="reservedRail">{Array.from({length: 8}, (_, index) => <span key={index} title="Reserved" />)}</div>
        <span aria-hidden="true" />
      </div> : null}
      <div className="surfaceCaption surfaceFooter">
        <span>{performance ? 'PERFORMANCE' : selected ? `SCENE ${selected.slot + 1}` : 'SELECTED AGENT'}</span>
        <span>{performance ? 'FULL SURFACE' : selected?.label ?? 'NO SESSION'}</span>
      </div>
    </div>
  );
}
