import {
  accentNames,
  agentStates,
  type AgentState,
  type ControlAction,
  type DemoManifest,
  type DemoStage,
  type SessionView,
  type SurfaceView,
} from './types';

export interface DemoState {
  manifest: DemoManifest;
  mode: 'guided' | 'sandbox';
  stage: string;
  sessions: SessionView[];
  frame: number;
  audioCue: string | null;
  audioSlot: number | null;
  audioSequence: number;
}

export type DemoEvent =
  | {type: 'select'; slot: number}
  | {type: 'action'; action: ControlAction}
  | {type: 'mode'; mode: 'guided' | 'sandbox'}
  | {type: 'set_state'; slot: number; state: AgentState}
  | {type: 'reset'};

export function createDemoState(manifest: DemoManifest): DemoState {
  return {
    manifest,
    mode: 'guided',
    stage: manifest.initial_stage,
    sessions: [],
    frame: 0,
    audioCue: stage(manifest, manifest.initial_stage).enter_audio,
    audioSlot: null,
    audioSequence: 1,
  };
}

export function demoReducer(state: DemoState, event: DemoEvent): DemoState {
  if (event.type === 'reset') return createDemoState(state.manifest);
  if (event.type === 'mode') {
    if (event.mode === 'sandbox' && !currentStage(state).terminal) return state;
    return event.mode === 'sandbox'
      ? {
          ...state,
          mode: 'sandbox',
          sessions: sandboxSessions(),
          frame: state.frame + 1,
          audioCue: null,
          audioSlot: null,
        }
      : createDemoState(state.manifest);
  }
  if (state.mode === 'sandbox') return sandboxReducer(state, event);
  if (event.type !== 'select' && event.type !== 'action') return state;
  const active = currentStage(state);
  const transition = active.transitions.find((candidate) => (
    event.type === 'select'
      ? candidate.event === 'select' && candidate.slot === event.slot
      : candidate.event === 'action' && candidate.action === event.action
  ));
  if (!transition) return state;
  const next = stage(state.manifest, transition.next_stage);
  const selected = active.view.sessions.find((session) => session.selected);
  return {
    ...state,
    stage: next.id,
    frame: state.frame + 1,
    audioCue: transition.audio ?? next.enter_audio,
    audioSlot: event.type === 'select' ? event.slot : selected?.slot ?? null,
    audioSequence: state.audioSequence + 1,
  };
}

export function demoSurfaceView(state: DemoState): SurfaceView {
  const sessions = state.mode === 'sandbox' ? state.sessions : currentStage(state).view.sessions;
  const selected = sessions.find((item) => item.selected) ?? null;
  return {
    selected_state: selected?.state ?? null,
    frame: state.frame,
    sessions,
    available_actions: state.mode === 'sandbox'
      ? sandboxActions(selected?.state)
      : currentStage(state).view.available_actions,
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
  return currentStage(state).prompt;
}

export function demoComplete(state: DemoState): boolean {
  return state.mode === 'guided' && currentStage(state).terminal;
}

function sandboxReducer(state: DemoState, event: DemoEvent): DemoState {
  if (event.type === 'set_state') {
    return updateSession(state, event.slot, {state: event.state});
  }
  if (event.type === 'select') {
    if (!state.sessions.some((item) => item.slot === event.slot)) return state;
    return {
      ...state,
      frame: state.frame + 1,
      sessions: state.sessions.map((item) => ({...item, selected: item.slot === event.slot})),
      audioCue: 'session_selected',
      audioSlot: event.slot,
      audioSequence: state.audioSequence + 1,
    };
  }
  if (event.type !== 'action') return state;
  const selected = state.sessions.find((item) => item.selected);
  if (!selected || !sandboxActions(selected.state).includes(event.action)) return state;
  const nextState = ({
    approve: 'success',
    reject: 'cancelled',
    stop: 'cancelled',
    retry: 'success',
  } satisfies Record<ControlAction, AgentState>)[event.action];
  return {
    ...updateSession(state, selected.slot, {state: nextState}),
    audioCue: event.action,
    audioSlot: selected.slot,
    audioSequence: state.audioSequence + 1,
  };
}

function currentStage(state: DemoState): DemoStage {
  return stage(state.manifest, state.stage);
}

function stage(manifest: DemoManifest, id: string): DemoStage {
  const selected = manifest.stages.find((item) => item.id === id);
  if (!selected) throw new Error(`Unknown Demo stage ${id}.`);
  return selected;
}

function sandboxActions(state: AgentState | undefined): ControlAction[] {
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
