import {
  type AgentState,
  type ControlAction,
  type DemoManifest,
  type DemoStage,
  type SurfaceView,
} from './types';

export interface DemoState {
  manifest: DemoManifest;
  stage: string;
  frame: number;
  audioCue: string | null;
  audioSlot: number | null;
  audioSequence: number;
}

export type DemoEvent =
  | {type: 'select'; slot: number}
  | {type: 'action'; action: ControlAction}
  | {type: 'reset'};

export function createDemoState(manifest: DemoManifest): DemoState {
  return {
    manifest,
    stage: manifest.initial_stage,
    frame: 0,
    audioCue: stage(manifest, manifest.initial_stage).enter_audio,
    audioSlot: null,
    audioSequence: 1,
  };
}

export function demoReducer(state: DemoState, event: DemoEvent): DemoState {
  if (event.type === 'reset') return {...createDemoState(state.manifest), audioSequence: state.audioSequence + 1};
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
  const sessions = currentStage(state).view.sessions;
  const selected = sessions.find((item) => item.selected) ?? null;
  return {
    selected_state: selected?.state ?? null,
    frame: state.frame,
    sessions,
    available_actions: currentStage(state).view.available_actions,
    overflow_count: 0,
    activity_motion: false,
  };
}

export function demoPrompt(state: DemoState): {eyebrow: string; title: string; detail: string} {
  return currentStage(state).prompt;
}

export function demoTarget(state: DemoState): DemoStage['guide_target'] {
  return currentStage(state).guide_target;
}

function currentStage(state: DemoState): DemoStage {
  return stage(state.manifest, state.stage);
}

function stage(manifest: DemoManifest, id: string): DemoStage {
  const selected = manifest.stages.find((item) => item.id === id);
  if (!selected) throw new Error(`Unknown Demo stage ${id}.`);
  return selected;
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
