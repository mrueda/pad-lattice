import {accentNames, agentStates, type AgentState, type ControlAction, type SessionView, type SurfaceView} from './types';

type BackgroundEvent =
  | {label: string; slot: number; state: AgentState}
  | {label: string; slot: number; disconnect: true};

interface Scenario {
  id: string;
  title: string;
  sessions: SessionView[];
  events: BackgroundEvent[];
}

function session(slot: number, label: string, state: AgentState, selected = false): SessionView {
  return {slot, label, state, selected, accent: accentNames[slot]};
}

export const playgroundScenarios: readonly Scenario[] = [
  {
    id: 'parallel', title: 'Three sessions at work',
    sessions: [session(0, 'Builder', 'running', true), session(1, 'Reviewer', 'waiting_for_approval'), session(2, 'Tests', 'error')],
    events: [
      {label: 'Builder finishes', slot: 0, state: 'success'},
      {label: 'Reviewer requests permission', slot: 1, state: 'waiting_for_approval'},
      {label: 'Tests finish', slot: 2, state: 'success'},
    ],
  },
  {
    id: 'resolved', title: 'Request answered elsewhere',
    sessions: [session(0, 'Builder', 'running'), session(1, 'Reviewer', 'waiting_for_approval', true), session(2, 'Tests', 'running')],
    events: [
      {label: 'Reviewer permission answered in Codex', slot: 1, state: 'running'},
      {label: 'Reviewer finishes', slot: 1, state: 'success'},
    ],
  },
  {
    id: 'disconnect', title: 'Selected session disconnects',
    sessions: [session(0, 'Builder', 'running'), session(1, 'Reviewer', 'waiting_for_approval', true), session(2, 'Tests', 'error')],
    events: [
      {label: 'Reviewer disconnects', slot: 1, disconnect: true},
      {label: 'Builder requests permission', slot: 0, state: 'waiting_for_approval'},
    ],
  },
  {
    id: 'vocabulary', title: 'All states / eight sessions',
    sessions: agentStates.map((state, slot) => session(slot, `Agent ${slot + 1}`, state, slot === 0)),
    events: [],
  },
];

export interface PlaygroundState {
  scenario: string;
  sessions: SessionView[];
  step: number;
  revision: number;
  sequence: number;
  history: {id: number; text: string; blocked: boolean}[];
  audioCue: string | null;
  audioSlot: number | null;
  audioSequence: number;
}

export type PlaygroundEvent =
  | {type: 'scenario'; id: string}
  | {type: 'reset'}
  | {type: 'advance'}
  | {type: 'select'; slot: number; expectedRevision: number}
  | {type: 'action'; action: ControlAction; expectedRevision: number}
  | {type: 'set_state'; slot: number; state: AgentState};

export function createPlaygroundState(id = 'parallel'): PlaygroundState {
  const scenario = playgroundScenarios.find((item) => item.id === id) ?? playgroundScenarios[0];
  return {
    scenario: scenario.id, sessions: scenario.sessions.map((item) => ({...item})),
    step: 0, revision: 0, sequence: 0,
    history: [{id: 0, text: scenario.title, blocked: false}],
    audioCue: null, audioSlot: null, audioSequence: 0,
  };
}

export function nextPlaygroundEvent(state: PlaygroundState): BackgroundEvent | undefined {
  return playgroundScenarios.find((item) => item.id === state.scenario)?.events[state.step];
}

function actions(state: AgentState | undefined): ControlAction[] {
  if (state === 'waiting_for_approval') return ['approve', 'reject'];
  if (state === 'running') return ['stop'];
  if (state === 'error' || state === 'cancelled') return ['retry'];
  return [];
}

export function playgroundView(state: PlaygroundState): SurfaceView {
  const selected = state.sessions.find((item) => item.selected);
  return {
    selected_state: selected?.state ?? null, sessions: state.sessions,
    available_actions: actions(selected?.state), control_revision: state.revision,
    frame: 0, overflow_count: 0, activity_motion: false,
  };
}

function record(state: PlaygroundState, text: string, blocked = false): PlaygroundState {
  const sequence = state.sequence + 1;
  return {...state, sequence, history: [...state.history, {id: sequence, text, blocked}].slice(-6)};
}

// This reducer is an isolated teaching model, never an agent or device transport.
export function playgroundReducer(state: PlaygroundState, event: PlaygroundEvent): PlaygroundState {
  if (event.type === 'scenario' || event.type === 'reset') {
    const next = createPlaygroundState(event.type === 'scenario' ? event.id : state.scenario);
    return {...next, revision: state.revision + 1, audioSequence: state.audioSequence + 1};
  }
  if ('expectedRevision' in event && event.expectedRevision !== state.revision) {
    return record(state, 'Outdated input ignored. No session changed.', true);
  }
  if (event.type === 'advance') {
    const next = nextPlaygroundEvent(state);
    if (!next) return state;
    return record({
      ...state, step: state.step + 1, revision: state.revision + 1,
      sessions: 'disconnect' in next
        ? state.sessions.filter((item) => item.slot !== next.slot)
        : state.sessions.map((item) => item.slot === next.slot ? {...item, state: next.state} : item),
      audioCue: null,
    }, next.label);
  }
  if (event.type === 'select') {
    const target = state.sessions.find((item) => item.slot === event.slot);
    if (!target || target.selected) return state;
    return record({
      ...state, revision: state.revision + 1,
      sessions: state.sessions.map((item) => ({...item, selected: item.slot === event.slot})),
      audioCue: 'session_selected', audioSlot: event.slot, audioSequence: state.audioSequence + 1,
    }, `Selected ${target.label} (Scene ${target.slot + 1}).`);
  }
  if (event.type === 'set_state') {
    const target = state.sessions.find((item) => item.slot === event.slot);
    if (!target || target.state === event.state) return state;
    return record({
      ...state, revision: state.revision + 1, audioCue: null,
      sessions: state.sessions.map((item) => item.slot === event.slot ? {...item, state: event.state} : item),
    }, `${target.label}: ${event.state.replaceAll('_', ' ')}.`);
  }
  const selected = state.sessions.find((item) => item.selected);
  if (!selected || !actions(selected.state).includes(event.action)) {
    return record(state, `${event.action}: unavailable. No session changed.`, true);
  }
  const nextState = event.action === 'approve' || event.action === 'retry' ? 'running' : 'cancelled';
  return record({
    ...state, revision: state.revision + 1,
    sessions: state.sessions.map((item) => item.slot === selected.slot ? {...item, state: nextState} : item),
    audioCue: event.action, audioSlot: selected.slot, audioSequence: state.audioSequence + 1,
  }, `${selected.label}: ${event.action} received; ${nextState === 'running' ? 'work resumed' : 'work cancelled'}.`);
}
