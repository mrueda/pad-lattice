import {
  Check,
  MoreHorizontal,
  RotateCcw,
  Square,
  X,
  type LucideIcon,
} from 'lucide-react';
import {tokenColor} from './surfaceModel';
import type {ControlAction, SurfaceView, VisualFrame} from './types';

interface Props {
  frame: VisualFrame;
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

export function VirtualSurface({frame, view, disabled = false, onAction, onSelect}: Props) {
  return (
    <div className="virtualSurface" aria-label="Pad-Lattice virtual control surface">
      <div className="surfaceCaption">
        <span>ACTIONS</span>
        <span>VISUAL PROTOCOL 1</span>
      </div>
      <div className="surfaceTop">
        <div className="topRail">
          {topControls.map((control, index) => {
            const token = control.action
              ? frame.actions[control.action]
              : control.system === 'overflow'
                ? frame.overflow
                : 'off';
            const enabled = !disabled && token !== 'off' && Boolean(control.action);
            const Icon = control.icon;
            return (
              <button
                className="railControl"
                disabled={!enabled}
                key={index}
                onClick={() => control.action && onAction(control.action)}
                style={{'--pad-color': tokenColor(token)} as React.CSSProperties}
                title={control.label}
                aria-label={control.label}>
                {Icon && token !== 'off' ? <Icon aria-hidden="true" /> : null}
              </button>
            );
          })}
        </div>
        <span aria-hidden="true" />
      </div>

      <div className="surfaceBody">
        <div className="matrixGrid" aria-label="Selected-agent state and agent status grid">
          {Array.from({length: 8}, (_, row) =>
            Array.from({length: 8}, (_, column) => {
              const token = column === 7 ? frame.statuses[row] : frame.state[row][column];
              const status = column === 7;
              const statusSession = status
                ? view.sessions.find((session) => session.slot === row)
                : undefined;
              return (
                <span
                  className={`matrixPad ${status ? 'statusPad' : ''}`}
                  key={`${row}-${column}`}
                  style={{'--pad-color': tokenColor(token)} as React.CSSProperties}
                  title={statusSession ? `${statusSession.label}: ${statusSession.state}` : undefined}
                />
              );
            }),
          )}
        </div>
        <div className="sceneRail" aria-label="Agent Scenes">
          {frame.selectors.map((token, slot) => {
            const session = view.sessions.find((item) => item.slot === slot);
            return (
              <button
                className="sceneControl"
                disabled={disabled || token === 'off'}
                key={slot}
                onClick={() => onSelect(slot)}
                style={{'--pad-color': tokenColor(token)} as React.CSSProperties}
                title={session ? `Select ${session.label}` : `Empty Scene ${slot + 1}`}
                aria-label={session ? `Select ${session.label}` : `Empty Scene ${slot + 1}`}>
                <span>{session ? slot + 1 : ''}</span>
              </button>
            );
          })}
        </div>
      </div>
      <div className="surfaceCaption surfaceFooter">
        <span>SELECTED AGENT</span>
        <span>{view.sessions.find((session) => session.selected)?.label ?? 'NO SESSION'}</span>
      </div>
    </div>
  );
}
