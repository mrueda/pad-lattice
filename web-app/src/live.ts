import {useCallback, useEffect, useRef, useState} from 'react';
import type {
  AuthenticatedMessage,
  ControlAction,
  PairingMessage,
  ServerMessage,
  SurfaceMessage,
} from './types';

const tokenKey = 'pad-lattice-session-token';

export type ConnectionState =
  | 'connecting'
  | 'connected'
  | 'pairing_required'
  | 'disconnected';

export interface LiveSurfaceState {
  connection: ConnectionState;
  surface: SurfaceMessage | null;
  pairing: PairingMessage | null;
  admin: boolean;
  lanEnabled: boolean;
  error: string | null;
  pair: (pin: string) => void;
  selectSession: (slot: number) => void;
  sendAction: (action: ControlAction) => void;
  createPairing: () => void;
  revokeRemote: () => void;
}

export function useLiveSurface(): LiveSurfaceState {
  const [connection, setConnection] = useState<ConnectionState>('connecting');
  const [surface, setSurface] = useState<SurfaceMessage | null>(null);
  const [pairing, setPairing] = useState<PairingMessage | null>(null);
  const [admin, setAdmin] = useState(false);
  const [lanEnabled, setLanEnabled] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<number | null>(null);
  const credentialRef = useRef<string | null>(initialCredential());
  const authenticatedRef = useRef(false);
  const authenticationRejectedRef = useRef(false);
  const stoppedRef = useRef(false);

  const connect = useCallback((credential?: string | null) => {
    if (credential !== undefined) credentialRef.current = credential;
    if (socketRef.current) {
      socketRef.current.onclose = null;
      socketRef.current.close();
    }
    if (retryRef.current !== null) window.clearTimeout(retryRef.current);
    setConnection('connecting');
    setError(null);
    authenticatedRef.current = false;
    authenticationRejectedRef.current = false;
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const socket = new WebSocket(`${scheme}://${window.location.host}/ws`);
    socketRef.current = socket;
    socket.onopen = () => {
      const credentialValue = credentialRef.current;
      socket.send(JSON.stringify({
        protocol: 1,
        type: 'authenticate',
        ...(credentialValue ? {credential: credentialValue} : {}),
      }));
    };
    socket.onmessage = (event) => {
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
          authenticationRejectedRef.current = true;
          window.localStorage.removeItem(tokenKey);
          credentialRef.current = null;
          setConnection('pairing_required');
        }
      }
    };
    socket.onerror = () => setError('Cannot reach the local Pad-Lattice bridge.');
    socket.onclose = () => {
      socketRef.current = null;
      if (stoppedRef.current) return;
      if (!authenticatedRef.current) {
        if (authenticationRejectedRef.current) {
          setConnection('pairing_required');
        } else {
          setConnection('disconnected');
          retryRef.current = window.setTimeout(() => connect(), 1200);
        }
        return;
      }
      setConnection('disconnected');
      retryRef.current = window.setTimeout(() => connect(), 1200);
    };

    function applyAuthentication(message: AuthenticatedMessage) {
      authenticatedRef.current = true;
      setAdmin(message.admin);
      setLanEnabled(message.lan_enabled);
      setConnection('connected');
      if (message.session_token) {
        credentialRef.current = message.session_token;
        window.localStorage.setItem(tokenKey, message.session_token);
      }
    }
  }, []);

  useEffect(() => {
    stoppedRef.current = false;
    connect();
    return () => {
      stoppedRef.current = true;
      if (retryRef.current !== null) window.clearTimeout(retryRef.current);
      socketRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((message: object) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({protocol: 1, ...message}));
    }
  }, []);

  return {
    connection,
    surface,
    pairing,
    admin,
    lanEnabled,
    error,
    pair: (pin) => connect(pin.replace(/\s/g, '')),
    selectSession: (slot) => send({type: 'select_session', slot}),
    sendAction: (action) => send({type: 'action', action}),
    createPairing: () => send({type: 'create_pairing'}),
    revokeRemote: () => send({type: 'revoke_remote'}),
  };
}

function initialCredential(): string | null {
  const hash = new URLSearchParams(window.location.hash.slice(1));
  const pairingSecret = hash.get('pair');
  if (pairingSecret) {
    window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`);
    return pairingSecret;
  }
  return window.localStorage.getItem(tokenKey);
}
