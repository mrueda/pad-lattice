import {useCallback, useEffect, useRef, useState} from 'react';
import {surfaceSocket, type SurfaceSocket} from './desktop';
import type {
  AuthenticatedMessage,
  ControlAction,
  ExperienceKind,
  ExperienceStateMessage,
  PairingMessage,
  PerformanceFrameMessage,
  ServerMessage,
  SurfaceMessage,
} from './types';

const tokenKey = 'pad-lattice-session-token';
const adminTokenKey = 'pad-lattice-admin-token';

export type ConnectionState =
  | 'connecting'
  | 'connected'
  | 'pairing_required'
  | 'disconnected';

export interface LiveSurfaceState {
  connection: ConnectionState;
  surface: SurfaceMessage | null;
  experience: ExperienceStateMessage | null;
  performanceFrame: PerformanceFrameMessage | null;
  pairing: PairingMessage | null;
  admin: boolean;
  lanEnabled: boolean;
  paused: boolean;
  controlsReady: boolean;
  reconnect: () => void;
  disconnect: () => void;
  error: string | null;
  pair: (pin: string) => void;
  selectSession: (slot: number) => void;
  sendAction: (action: ControlAction) => void;
  questionRequest: (operation: 'status' | 'answer', params?: object) => Promise<unknown>;
  createPairing: () => void;
  revokeRemote: () => void;
  startExperience: (kind: ExperienceKind) => void;
  stopExperience: () => void;
}

export function useLiveSurface(onAudioCue?: (cue: string, slot: number | null) => void): LiveSurfaceState {
  const audioCallback = useRef(onAudioCue);
  audioCallback.current = onAudioCue;
  const [connection, setConnection] = useState<ConnectionState>('connecting');
  const [surface, setSurface] = useState<SurfaceMessage | null>(null);
  const [experience, setExperience] = useState<ExperienceStateMessage | null>(null);
  const [performanceFrame, setPerformanceFrame] = useState<PerformanceFrameMessage | null>(null);
  const [pairing, setPairing] = useState<PairingMessage | null>(null);
  const [admin, setAdmin] = useState(false);
  const [lanEnabled, setLanEnabled] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);
  const socketRef = useRef<SurfaceSocket | null>(null);
  const credentialRef = useRef<string | null>(initialCredential());
  const authenticatedRef = useRef(false);
  const authenticationRejectedRef = useRef(false);
  const stoppedRef = useRef(false);
  const questionPending = useRef(new Map<string, {resolve: (value: unknown) => void; reject: (error: Error) => void; timer: number}>());
  const questionSequence = useRef(0);
  const cancelQuestions = useCallback(() => {
    for (const pending of questionPending.current.values()) {
      clearTimeout(pending.timer);
      pending.reject(new Error('Connection closed. Reconnect and try again.'));
    }
    questionPending.current.clear();
  }, []);

  const connect = useCallback((credential?: string | null) => {
    cancelQuestions();
    stoppedRef.current = false;
    setPaused(false);
    if (credential !== undefined) credentialRef.current = credential;
    if (socketRef.current) {
      socketRef.current.onopen = socketRef.current.onmessage = socketRef.current.onerror = socketRef.current.onclose = null;
      socketRef.current.close();
    }
    setConnection('connecting');
    setSurface(null);
    setExperience(null);
    setPerformanceFrame(null);
    setPairing(null);
    setAdmin(false);
    setError(null);
    authenticatedRef.current = false;
    authenticationRejectedRef.current = false;
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const socket = surfaceSocket(`${scheme}://${window.location.host}/ws`);
    socketRef.current = socket;
    socket.onopen = () => {
      if (socketRef.current !== socket || stoppedRef.current) return;
      const credentialValue = credentialRef.current;
      socket.send(JSON.stringify({
        protocol: 1,
        type: 'authenticate',
        ...(credentialValue ? {credential: credentialValue} : {}),
      }));
    };
    socket.onmessage = (event) => {
      if (socketRef.current !== socket || stoppedRef.current) return;
      let message: ServerMessage;
      try {
        message = JSON.parse(String(event.data)) as ServerMessage;
      } catch {
        setError('The local bridge sent an invalid message.');
        return;
      }
      if (message.protocol !== 1) {
        setError('The local bridge uses an unsupported protocol.');
        return;
      }
      if (message.type === 'authenticated') {
        applyAuthentication(message);
        return;
      }
      if (message.type === 'surface') {
        setSurface(message);
        return;
      }
      if (message.type === 'question_response') {
        const pending = questionPending.current.get(message.request_id);
        if (pending) {
          questionPending.current.delete(message.request_id);
          clearTimeout(pending.timer);
          if (message.error) pending.reject(new Error(message.error));
          else pending.resolve(message.result);
        }
        return;
      }
      if (message.type === 'device_disconnected') {
        stoppedRef.current = true;
        cancelQuestions();
        setPaused(true);
        setConnection('disconnected');
        setSurface(null);
        setExperience(null);
        setPerformanceFrame(null);
        setError('Disconnected from Desktop.');
        return;
      }
      if (message.type === 'audio_cue') {
        audioCallback.current?.(message.cue, message.slot);
        return;
      }
      if (message.type === 'experience_state') {
        setExperience(message);
        if (message.status === 'idle' || message.status === 'blocked') {
          setPerformanceFrame(null);
        }
        return;
      }
      if (message.type === 'performance_frame') {
        setPerformanceFrame(message);
        return;
      }
      if (message.type === 'pairing') {
        setPairing(message);
        return;
      }
      if (message.type === 'remote_revoked') {
        setPairing(null);
        return;
      }
      if (message.type === 'error') {
        setError(message.error);
        if (message.code === 'forbidden' || message.code === 'authentication_timeout') {
          cancelQuestions();
          authenticatedRef.current = false;
          authenticationRejectedRef.current = true;
          window.localStorage.removeItem(tokenKey);
          window.localStorage.removeItem(adminTokenKey);
          credentialRef.current = null;
          setConnection('pairing_required');
          setSurface(null);
          setExperience(null);
          setPerformanceFrame(null);
        }
      }
    };
    socket.onerror = () => setError('Cannot reach the local Pad-Lattice bridge.');
    socket.onclose = () => {
      if (socketRef.current !== socket) return;
      cancelQuestions();
      socketRef.current = null;
      setSurface(null);
      setExperience(null);
      setPerformanceFrame(null);
      setPairing(null);
      if (stoppedRef.current) return;
      if (authenticationRejectedRef.current) {
        setConnection('pairing_required');
        return;
      }
      stoppedRef.current = true;
      setPaused(true);
      setConnection('disconnected');
      setError(authenticatedRef.current ? 'Desktop disconnected.' : 'Cannot reach Pad-Lattice.');
      authenticatedRef.current = false;
      setAdmin(false);
    };

    function applyAuthentication(message: AuthenticatedMessage) {
      authenticatedRef.current = true;
      setAdmin(message.admin);
      setLanEnabled(message.lan_enabled);
      setConnection('connected');
      setError(null);
      if (message.session_token) {
        credentialRef.current = message.session_token;
        window.localStorage.setItem(tokenKey, message.session_token);
      }
    }
  }, [cancelQuestions]);

  useEffect(() => {
    stoppedRef.current = false;
    connect();
    return () => {
      stoppedRef.current = true;
      cancelQuestions();
      const socket = socketRef.current;
      socketRef.current = null;
      if (socket) {
        socket.onopen = socket.onmessage = socket.onerror = socket.onclose = null;
        socket.close();
      }
    };
  }, [connect, cancelQuestions]);

  const send = useCallback((message: object) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({protocol: 1, ...message}));
    }
  }, []);

  const revision = surface?.view.control_revision;
  const hasRevision = typeof revision === 'number' && Number.isSafeInteger(revision) && revision >= 0;
  // Standalone Demo has no agent control plane. Daemon-hosted Demo carries
  // its starting revision so a late Demo click cannot reach a newly joined agent.
  const standaloneDemo = revision == null && experience?.kind === 'demo'
    && experience.status === 'playing';
  const controlsReady = connection === 'connected' && surface !== null && (hasRevision || standaloneDemo);
  const sendControl = (message: object) => {
    if (!controlsReady || !authenticatedRef.current || stoppedRef.current) return;
    send({...message, ...(hasRevision ? {expected_revision: revision} : {})});
  };
  const questionRequest = useCallback((operation: 'status' | 'answer', params: object = {}) => new Promise<unknown>((resolve, reject) => {
    if (!authenticatedRef.current || stoppedRef.current || socketRef.current?.readyState !== WebSocket.OPEN) {
      reject(new Error('The surface is disconnected.')); return;
    }
    const requestId = String(++questionSequence.current);
    const timer = window.setTimeout(() => {
      questionPending.current.delete(requestId);
      reject(new Error('Question request timed out.'));
    }, 5000);
    questionPending.current.set(requestId, {resolve, reject, timer});
    try {socketRef.current.send(JSON.stringify({protocol: 1, type: 'question_request', request_id: requestId, operation, ...params}));}
    catch {
      clearTimeout(timer);
      questionPending.current.delete(requestId);
      reject(new Error('Could not send the question request.'));
    }
  }), []);

  return {
    connection,
    surface,
    experience,
    performanceFrame,
    pairing,
    admin,
    lanEnabled,
    paused,
    controlsReady,
    reconnect: () => connect(),
    disconnect: () => {
      stoppedRef.current = true;
      cancelQuestions();
      const socket = socketRef.current;
      socketRef.current = null;
      if (socket) {
        socket.onopen = socket.onmessage = socket.onerror = socket.onclose = null;
        socket.close();
      }
      authenticatedRef.current = false;
      setPaused(true);
      setConnection('disconnected');
      setSurface(null);
      setExperience(null);
      setPerformanceFrame(null);
      setPairing(null);
      setAdmin(false);
      setError('Disconnected on this device.');
    },
    error,
    pair: (pin) => connect(pin.replace(/\s/g, '')),
    selectSession: (slot) => sendControl({type: 'select_session', slot}),
    sendAction: (action) => sendControl({type: 'action', action}),
    questionRequest,
    createPairing: () => {setPairing(null); setError(null); send({type: 'create_pairing'});},
    revokeRemote: () => send({type: 'revoke_remote'}),
    startExperience: (kind) => send({type: 'start_experience', kind}),
    stopExperience: () => send({type: 'stop_experience'}),
  };
}

function initialCredential(): string | null {
  const hash = new URLSearchParams(window.location.hash.slice(1));
  const adminSecret = hash.get('admin');
  if (adminSecret) {
    window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`);
    window.localStorage.setItem(adminTokenKey, adminSecret);
    return adminSecret;
  }
  const pairingSecret = hash.get('pair');
  if (pairingSecret) {
    window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`);
    return pairingSecret;
  }
  return window.localStorage.getItem(adminTokenKey) ?? window.localStorage.getItem(tokenKey);
}
