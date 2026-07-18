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
  | ErrorMessage
  | {protocol: 1; type: 'remote_revoked'};
