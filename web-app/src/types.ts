export const agentStates = [
  'running',
  'waiting_for_reply',
  'user_typing',
  'waiting_for_approval',
  'success',
  'error',
  'cancelled',
] as const;

export const controlActions = ['approve', 'reject', 'stop', 'retry'] as const;

export const accentNames = [
  'cyan',
  'magenta',
  'lime',
  'orange',
  'violet',
  'teal',
  'rose',
  'sky',
] as const;

export type AgentState = (typeof agentStates)[number];
export type ControlAction = (typeof controlActions)[number];
export type AccentName = (typeof accentNames)[number];

export interface SessionView {
  slot: number;
  state: AgentState;
  selected: boolean;
  accent: AccentName;
  label: string;
}

export interface SurfaceView {
  selected_state: AgentState | null;
  frame: number;
  sessions: SessionView[];
  available_actions: ControlAction[];
  overflow_count: number;
  activity_motion: boolean;
}

export interface VisualFrame {
  state: string[][];
  selectors: string[];
  statuses: string[];
  actions: Record<ControlAction, string>;
  overflow: string;
}

export interface FullSurfaceFrame {
  grid: string[][];
  top: string[];
  right: string[];
}

export type ExperienceKind = 'demo' | 'show';
export type ExperienceStatus = 'idle' | 'blocked' | 'starting' | 'playing';

export interface ExperienceStateMessage {
  protocol: 1;
  type: 'experience_state';
  status: ExperienceStatus;
  kind: ExperienceKind | null;
  title: string | null;
  cue_index: number | null;
  caption: string | null;
  detail: string | null;
  elapsed_ms: number;
  duration_ms: number | null;
  tempo: number;
  audio_asset: string | null;
  audio_cue: string | null;
  audio_slot: number | null;
  audio_sequence: number;
  start_delay_ms: number;
  reason: string | null;
}

export interface PerformanceFrameMessage extends FullSurfaceFrame {
  protocol: 1;
  type: 'performance_frame';
}

export interface PerformanceManifest {
  schema_version: 1;
  kind: 'performance';
  id: string;
  title: string;
  dimensions: {grid: [8, 8]; top: 8; right: 8};
  duration_ms: number;
  acts: string[];
  palette: {fallback: string; rgb: [number, number, number]}[];
  cues: {
    act: number;
    duration_ms: number;
    caption: string | null;
    frame: {grid: number[][]; top: number[]; right: number[]};
  }[];
  audio: {asset: string; mime_type: 'audio/wav'; duration_ms: number};
}

export interface DemoManifest {
  schema_version: 1;
  kind: 'demo';
  id: string;
  title: string;
  initial_stage: string;
  stages: DemoStage[];
}

export interface DemoStage {
  id: string;
  prompt: {eyebrow: string; title: string; detail: string};
  guide_target: {
    event: 'select' | 'action';
    slot: number | null;
    action: ControlAction | null;
  } | null;
  view: {sessions: SessionView[]; available_actions: ControlAction[]};
  transitions: {
    event: 'select' | 'action';
    slot: number | null;
    action: ControlAction | null;
    next_stage: string;
    audio: string | null;
  }[];
  enter_audio: string | null;
  terminal: boolean;
}

export interface SurfaceMessage {
  protocol: 1;
  type: 'surface';
  visual_protocol: 1;
  view: SurfaceView;
  visual_frame: VisualFrame;
}

export interface PairingMessage {
  protocol: 1;
  type: 'pairing';
  pin: string;
  pairing_url: string;
  qr_data_uri: string;
  expires_in: number;
}

export interface AuthenticatedMessage {
  protocol: 1;
  type: 'authenticated';
  admin: boolean;
  session_token: string | null;
  lan_enabled: boolean;
}

export interface ErrorMessage {
  protocol: 1;
  type: 'error';
  code: string;
  error: string;
}

export type ServerMessage =
  | SurfaceMessage
  | PairingMessage
  | AuthenticatedMessage
  | ExperienceStateMessage
  | PerformanceFrameMessage
  | ErrorMessage
  | {protocol: 1; type: 'remote_revoked'};
