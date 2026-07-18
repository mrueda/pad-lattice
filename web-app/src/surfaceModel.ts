import {
  accentNames,
  agentStates,
  controlActions,
  type AccentName,
  type AgentState,
  type ControlAction,
  type SurfaceView,
  type VisualFrame,
} from './types';

type Coordinate = readonly [number, number];

const glyphs: Record<AgentState, readonly Coordinate[]> = {
  running: [
    [1, 3], [1, 4], [3, 3], [3, 4], [5, 3], [5, 4],
  ],
  waiting_for_reply: [
    [1, 0], [2, 0], [3, 0], [4, 0], [5, 0], [0, 1], [6, 1],
    [6, 2], [5, 2], [5, 3], [4, 3], [4, 4], [3, 5], [3, 7],
  ],
  user_typing: [
    [1, 1], [2, 2], [3, 3], [4, 4], [3, 5], [2, 6], [1, 7],
  ],
  waiting_for_approval: [
    [3, 0], [3, 1], [3, 2], [3, 3], [3, 4], [3, 7],
  ],
  success: [
    [1, 2], [5, 2], [0, 4], [1, 5], [2, 6], [3, 7], [4, 6], [5, 5], [6, 4],
  ],
  error: [
    [0, 0], [6, 0], [1, 1], [5, 1], [2, 2], [4, 2], [3, 3],
    [3, 4], [2, 5], [4, 5], [1, 6], [5, 6], [0, 7], [6, 7],
  ],
  cancelled: [
    [1, 1], [2, 1], [3, 1], [4, 1], [5, 1], [1, 2], [5, 2],
    [1, 3], [5, 3], [1, 4], [5, 4], [1, 5], [5, 5], [1, 6],
    [2, 6], [3, 6], [4, 6], [5, 6],
  ],
};

export function compileVisualFrame(view: SurfaceView): VisualFrame {
  const state = Array.from({length: 8}, () => Array.from({length: 7}, () => 'off'));
  if (view.selected_state === null) {
    for (const x of [2, 3, 4]) state[4][x] = 'idle';
  } else {
    const token = `state:${view.selected_state}:primary`;
    for (const [x, y] of glyphs[view.selected_state]) state[y][x] = token;
    if (view.selected_state === 'running' && view.activity_motion) {
      const x = [1, 3, 5][view.frame % 3];
      state[3][x] = 'activity';
      state[4][x] = 'activity';
    }
  }

  const selectors = Array.from({length: 8}, () => 'off');
  const statuses = Array.from({length: 8}, () => 'off');
  for (const session of view.sessions) {
    if (session.slot < 0 || session.slot >= 8) continue;
    selectors[session.slot] = `accent:${session.accent}:${session.selected ? 'selected' : 'unselected'}`;
    statuses[session.slot] = `state:${session.state}:summary`;
  }

  return {
    state,
    selectors,
    statuses,
    actions: Object.fromEntries(
      controlActions.map((action) => [
        action,
        view.available_actions.includes(action) ? `action:${action}:enabled` : 'off',
      ]),
    ) as Record<ControlAction, string>,
    overflow: view.overflow_count > 0 ? 'system:overflow' : 'off',
  };
}

export const accentRgb: Record<AccentName, readonly [number, number, number]> = {
  cyan: [0, 174, 187],
  magenta: [200, 62, 201],
  lime: [112, 185, 45],
  orange: [230, 126, 34],
  violet: [118, 86, 199],
  teal: [0, 155, 131],
  rose: [217, 76, 118],
  sky: [55, 136, 216],
};

const stateColors: Record<AgentState, {primary: string; summary: string}> = {
  running: {primary: '#3389e8', summary: '#245f9d'},
  waiting_for_reply: {primary: '#f2f5f7', summary: '#8e99a2'},
  user_typing: {primary: '#14bcc7', summary: '#087b83'},
  waiting_for_approval: {primary: '#f0b63f', summary: '#9c7628'},
  success: {primary: '#55c76a', summary: '#347d43'},
  error: {primary: '#ef5b64', summary: '#963d43'},
  cancelled: {primary: '#84909a', summary: '#505960'},
};

export function tokenColor(token: string): string {
  if (token === 'off') return '#11171c';
  if (token === 'idle') return '#46535c';
  if (token === 'activity') return '#a9d5ff';
  if (token === 'system:overflow') return '#f0b63f';
  if (token.startsWith('state:')) {
    const [, state, role] = token.split(':') as [string, AgentState, 'primary' | 'summary'];
    return stateColors[state]?.[role] ?? '#11171c';
  }
  if (token.startsWith('action:')) {
    const action = token.split(':')[1] as ControlAction;
    return {
      approve: '#55c76a',
      reject: '#ef5b64',
      retry: '#3389e8',
      stop: '#ef5b64',
    }[action];
  }
  if (token.startsWith('accent:')) {
    const [, name, role] = token.split(':') as [string, AccentName, string];
    const [red, green, blue] = accentRgb[name];
    return role === 'selected'
      ? `rgb(${red} ${green} ${blue})`
      : `rgb(${Math.round(red * 0.48)} ${Math.round(green * 0.48)} ${Math.round(blue * 0.48)})`;
  }
  return '#11171c';
}

export function isAgentState(value: unknown): value is AgentState {
  return typeof value === 'string' && agentStates.includes(value as AgentState);
}

export function isAccentName(value: unknown): value is AccentName {
  return typeof value === 'string' && accentNames.includes(value as AccentName);
}
