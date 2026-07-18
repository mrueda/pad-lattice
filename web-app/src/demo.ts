import {
  accentNames,
  agentStates,
  type AgentState,
  type ControlAction,
  type SessionView,
  type SurfaceView,
} from './types';

export type DemoStage =
  | 'select_reviewer'
  | 'approve_reviewer'
  | 'recover_reviewer'
  | 'select_tests'
  | 'retry_tests'
  | 'complete';

export interface DemoState {
  mode: 'guided' | 'sandbox';
  stage: DemoStage;
  sessions: SessionView[];
  frame: number;
}

export type DemoEvent =
  | {type: 'select'; slot: number}
  | {type: 'action'; action: ControlAction}
  | {type: 'mode'; mode: 'guided' | 'sandbox'}
  | {type: 'set_state'; slot: number; state: AgentState}
  | {type: 'reset'};

export const initialDemoState: DemoState = {
  mode: 'guided',
  stage: 'select_reviewer',
  frame: 0,
  sessions: [
    session(0, 'running', true, 'Builder'),
    session(1, 'waiting_for_approval', false, 'Reviewer'),
    session(2, 'error', false, 'Tests'),
  ],
};

export function demoReducer(state: DemoState, event: DemoEvent): DemoState {
  if (event.type === 'reset') return structuredClone(initialDemoState);
  if (event.type === 'mode') {
    if (event.mode === 'sandbox' && state.stage !== 'complete') return state;
    return event.mode === 'sandbox'
      ? {mode: 'sandbox', stage: 'complete', frame: state.frame + 1, sessions: sandboxSessions()}
      : structuredClone(initialDemoState);
  }
  if (event.type === 'set_state' && state.mode === 'sandbox') {
    return updateSession(state, event.slot, {state: event.state});
  }
  if (event.type === 'select') {
    if (!state.sessions.some((item) => item.slot === event.slot)) return state;
    let next = {
      ...state,
      frame: state.frame + 1,
      sessions: state.sessions.map((item) => ({...item, selected: item.slot === event.slot})),
    };
    if (state.stage === 'select_reviewer' && event.slot === 1) {
      next = {...next, stage: 'approve_reviewer'};
    } else if (state.stage === 'select_tests' && event.slot === 2) {
      next = {...next, stage: 'retry_tests'};
    }
    return next;
  }
  if (event.type === 'action') return applyAction(state, event.action);
  return state;
}

export function demoSurfaceView(state: DemoState): SurfaceView {
  const selected = state.sessions.find((item) => item.selected) ?? null;
  return {
    selected_state: selected?.state ?? null,
    frame: state.frame,
    sessions: state.sessions,
    available_actions: selected ? availableActions(selected.state, state) : [],
    overflow_count: 0,
    activity_motion: false,
  };
}

export function demoPrompt(state: DemoState): {eyebrow: string; title: string; detail: string} {
  if (state.mode === 'sandbox') {
    return {
      eyebrow: 'Protocol sandbox',
      title: 'Every scene is yours.',
      detail: 'Change an agent state, select its Scene, and use any action that lights up.',
    };
  }
  return {
    select_reviewer: {
      eyebrow: 'Three agents, one surface',
      title: 'The Reviewer needs you.',
      detail: 'Select its magenta Scene on the right rail.',
    },
    approve_reviewer: {
      eyebrow: 'Permission requested',
      title: 'Approve the review.',
      detail: 'The green action on the top rail is available now.',
    },
    recover_reviewer: {
      eyebrow: 'Decision registered',
      title: 'The Reviewer was rejected.',
      detail: 'Use Retry on the top rail to bring it back.',
    },
    select_tests: {
      eyebrow: 'Progress continues in parallel',
      title: 'The Tests need attention.',
      detail: 'Select the lime Scene beside the red status light.',
    },
    retry_tests: {
      eyebrow: 'Failure is actionable',
      title: 'Retry the test agent.',
      detail: 'The blue action on the top rail is ready.',
    },
    complete: {
      eyebrow: 'One visual language',
      title: 'The agents form a constellation.',
      detail: 'Every color has an identity. Every shape has a state. The sandbox is now open.',
    },
  }[state.stage];
}

function applyAction(state: DemoState, action: ControlAction): DemoState {
  const selected = state.sessions.find((item) => item.selected);
  if (!selected || !availableActions(selected.state, state).includes(action)) return state;

  if (state.mode === 'sandbox') {
    const nextState = ({
      approve: 'success',
      reject: 'cancelled',
      stop: 'cancelled',
      retry: 'success',
    } satisfies Record<ControlAction, AgentState>)[action];
    return updateSession(state, selected.slot, {state: nextState});
  }
  if (state.stage === 'approve_reviewer' && action === 'approve') {
    return {
      ...updateSession(state, 1, {state: 'success'}),
      stage: 'select_tests',
    };
  }
  if (state.stage === 'approve_reviewer' && action === 'reject') {
    return {
      ...updateSession(state, 1, {state: 'cancelled'}),
      stage: 'recover_reviewer',
    };
  }
  if (state.stage === 'recover_reviewer' && action === 'retry') {
    return {
      ...updateSession(state, 1, {state: 'success'}),
      stage: 'select_tests',
    };
  }
  if (state.stage === 'retry_tests' && action === 'retry') {
    const testsDone = updateSession(state, 2, {state: 'success'});
    const allDone = updateSession(testsDone, 0, {state: 'success'});
    return {...allDone, stage: 'complete'};
  }
  return state;
}

function availableActions(state: AgentState, demo: DemoState): ControlAction[] {
  if (demo.mode === 'guided') {
    if (demo.stage === 'approve_reviewer') return ['approve', 'reject'];
    if (demo.stage === 'recover_reviewer' || demo.stage === 'retry_tests') return ['retry'];
    return [];
  }
  if (state === 'waiting_for_approval') return ['approve', 'reject'];
  if (state === 'running') return ['stop'];
  if (state === 'error' || state === 'cancelled') return ['retry'];
  return [];
}

function updateSession(
  state: DemoState,
  slot: number,
  patch: Partial<SessionView>,
): DemoState {
  return {
    ...state,
    frame: state.frame + 1,
    sessions: state.sessions.map((item) => item.slot === slot ? {...item, ...patch} : item),
  };
}

function session(
  slot: number,
  state: AgentState,
  selected: boolean,
  label: string,
): SessionView {
  return {slot, state, selected, label, accent: accentNames[slot]};
}

function sandboxSessions(): SessionView[] {
  const states: AgentState[] = [
    'waiting_for_reply',
    'running',
    'user_typing',
    'waiting_for_approval',
    'success',
    'error',
    'cancelled',
    'waiting_for_reply',
  ];
  return states.map((state, slot) => session(slot, state, slot === 0, `Agent ${slot + 1}`));
}

export const stateLabels: Record<AgentState, string> = {
  running: 'Running',
  waiting_for_reply: 'Waiting for reply',
  user_typing: 'User typing',
  waiting_for_approval: 'Waiting for approval',
  success: 'Success',
  error: 'Error',
  cancelled: 'Cancelled',
};

export function validDemoState(value: string): value is AgentState {
  return agentStates.includes(value as AgentState);
}
