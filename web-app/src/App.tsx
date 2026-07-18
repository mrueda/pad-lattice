import {useEffect, useMemo, useReducer, useState, type FormEvent} from 'react';
import {
  BookOpen,
  ExternalLink,
  Link2,
  MonitorSmartphone,
  RefreshCw,
  ShieldCheck,
  ShieldOff,
  Wifi,
  WifiOff,
} from 'lucide-react';
import {
  demoPrompt,
  demoReducer,
  demoSurfaceView,
  initialDemoState,
  stateLabels,
  validDemoState,
} from './demo';
import {useLiveSurface} from './live';
import {compileVisualFrame, tokenColor} from './surfaceModel';
import type {AgentState, ControlAction, SessionView, SurfaceView, VisualFrame} from './types';
import {VirtualSurface} from './VirtualSurface';

type AppMode = 'loading' | 'demo' | 'live';

export default function App() {
  const [mode, setMode] = useState<AppMode>('loading');
  useEffect(() => {
    fetch('./config.json', {cache: 'no-store'})
      .then((response) => response.json())
      .then((config: {mode?: string; protocol?: number}) => {
        setMode(config.mode === 'live' && config.protocol === 1 ? 'live' : 'demo');
      })
      .catch(() => setMode('demo'));
  }, []);

  if (mode === 'loading') return <Loading />;
  return mode === 'live' ? <LiveApp /> : <DemoApp />;
}

function DemoApp() {
  const [demo, dispatch] = useReducer(demoReducer, initialDemoState);
  const view = demoSurfaceView(demo);
  const frame = useMemo(() => compileVisualFrame(view), [view]);
  const prompt = demoPrompt(demo);
  return (
    <PageFrame modeLabel="PUBLIC SIMULATION" connected>
      <div className="workspace">
        <section className="surfaceWorkspace">
          <VirtualSurface
            frame={frame}
            view={view}
            onAction={(action) => dispatch({type: 'action', action})}
            onSelect={(slot) => dispatch({type: 'select', slot})}
          />
        </section>
        <aside className="contextPane">
          <div className="modeSwitch" aria-label="Demo mode">
            <button
              className={demo.mode === 'guided' ? 'active' : ''}
              onClick={() => dispatch({type: 'mode', mode: 'guided'})}>Guided</button>
            <button
              className={demo.mode === 'sandbox' ? 'active' : ''}
              disabled={demo.stage !== 'complete'}
              onClick={() => dispatch({type: 'mode', mode: 'sandbox'})}>Sandbox</button>
          </div>

          <section className="narrative" aria-live="polite">
            <span>{prompt.eyebrow}</span>
            <h1>{prompt.title}</h1>
            <p>{prompt.detail}</p>
          </section>

          <SessionList
            sessions={view.sessions}
            sandbox={demo.mode === 'sandbox'}
            onSelect={(slot) => dispatch({type: 'select', slot})}
            onState={(slot, state) => dispatch({type: 'set_state', slot, state})}
          />

          <div className="paneActions">
            <button className="textButton" onClick={() => dispatch({type: 'reset'})}>
              <RefreshCw aria-hidden="true" /> Reset story
            </button>
            <a
              className="textButton"
              href="https://mrueda.github.io/pad-lattice/docs/overview"
              target="_top">
              <BookOpen aria-hidden="true" /> Documentation
            </a>
          </div>
        </aside>
      </div>
    </PageFrame>
  );
}

function LiveApp() {
  const live = useLiveSurface();
  const [pin, setPin] = useState('');
  const empty = emptySurface();
  const view = live.surface?.view ?? empty.view;
  const frame = live.surface?.visual_frame ?? empty.frame;
  const submitPin = (event: FormEvent) => {
    event.preventDefault();
    if (/^\d{6}$/.test(pin.replace(/\s/g, ''))) live.pair(pin);
  };
  return (
    <PageFrame
      modeLabel="LIVE CODEX"
      connected={live.connection === 'connected'}>
      <div className="workspace">
        <section className="surfaceWorkspace">
          <VirtualSurface
            disabled={live.connection !== 'connected'}
            frame={frame}
            view={view}
            onAction={live.sendAction}
            onSelect={live.selectSession}
          />
        </section>
        <aside className="contextPane">
          <ConnectionSummary state={live.connection} error={live.error} />

          {live.connection === 'pairing_required' ? (
            <form className="pairForm" onSubmit={submitPin}>
              <span>PAIR THIS DEVICE</span>
              <h1>Enter the six-digit PIN.</h1>
              <input
                aria-label="Pairing PIN"
                autoComplete="one-time-code"
                inputMode="numeric"
                maxLength={6}
                onChange={(event) => setPin(event.target.value.replace(/\D/g, ''))}
                pattern="[0-9]{6}"
                placeholder="000000"
                value={pin}
              />
              <button className="primaryButton" type="submit" disabled={pin.length !== 6}>
                <Link2 aria-hidden="true" /> Pair
              </button>
            </form>
          ) : null}

          {live.connection === 'connected' ? (
            <SessionList sessions={view.sessions} onSelect={live.selectSession} />
          ) : null}

          {live.admin && live.lanEnabled ? (
            <PairingPanel
              pairing={live.pairing}
              onCreate={live.createPairing}
              onRevoke={live.revokeRemote}
            />
          ) : null}
        </aside>
      </div>
    </PageFrame>
  );
}

function PageFrame({
  children,
  modeLabel,
  connected,
}: {
  children: React.ReactNode;
  modeLabel: string;
  connected: boolean;
}) {
  return (
    <main className="appPage">
      <header className="appHeader">
        <a className="brand" href="../" target="_top">
          <img src="./pad-lattice-logo.svg" alt="" />
          <span><strong>Pad-Lattice</strong><small>Virtual Surface</small></span>
        </a>
        <div className="headerStatus">
          <span className={connected ? 'connectionDot connected' : 'connectionDot'} />
          <span>{modeLabel}</span>
        </div>
      </header>
      {children}
      <footer className="appFooter">
        <span>Physical and virtual control surfaces for AI agents.</span>
        <a href="https://github.com/mrueda/pad-lattice" target="_blank" rel="noreferrer">
          GitHub <ExternalLink aria-hidden="true" />
        </a>
      </footer>
    </main>
  );
}

function SessionList({
  sessions,
  sandbox = false,
  onSelect,
  onState,
}: {
  sessions: SessionView[];
  sandbox?: boolean;
  onSelect: (slot: number) => void;
  onState?: (slot: number, state: AgentState) => void;
}) {
  return (
    <section className="sessionSection">
      <div className="sectionTitle"><span>AGENT SCENES</span><span>{sessions.length}/8</span></div>
      <div className="sessionList">
        {sessions.map((session) => (
          <div className={`sessionRow ${session.selected ? 'selected' : ''}`} key={session.slot}>
            <button onClick={() => onSelect(session.slot)} title={`Select ${session.label}`}>
              <i style={{backgroundColor: tokenColor(`accent:${session.accent}:selected`)}} />
              <span><strong>{session.label}</strong><small>Scene {session.slot + 1}</small></span>
            </button>
            {sandbox && onState ? (
              <select
                aria-label={`${session.label} state`}
                onChange={(event) => validDemoState(event.target.value) && onState(session.slot, event.target.value)}
                value={session.state}>
                {Object.entries(stateLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            ) : (
              <span className="stateLabel">{stateLabels[session.state]}</span>
            )}
          </div>
        ))}
        {sessions.length === 0 ? (
          <div className="emptySessions">
            <MonitorSmartphone aria-hidden="true" />
            <span><strong>No active agents</strong><small>Codex sessions will appear here.</small></span>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function ConnectionSummary({state, error}: {state: string; error: string | null}) {
  const online = state === 'connected';
  return (
    <section className={`connectionSummary ${online ? 'online' : ''}`} aria-live="polite">
      {online ? <Wifi aria-hidden="true" /> : <WifiOff aria-hidden="true" />}
      <span>
        <strong>{online ? 'Connected to Codex' : state.replace('_', ' ')}</strong>
        <small>{error ?? (online ? 'State and actions are synchronized.' : 'Waiting for the local bridge.')}</small>
      </span>
    </section>
  );
}

function PairingPanel({
  pairing,
  onCreate,
  onRevoke,
}: {
  pairing: ReturnType<typeof useLiveSurface>['pairing'];
  onCreate: () => void;
  onRevoke: () => void;
}) {
  return (
    <section className="pairingPanel">
      <div className="sectionTitle"><span>PHONE &amp; TABLET</span><ShieldCheck aria-hidden="true" /></div>
      {pairing ? (
        <div className="pairingContent">
          <img src={pairing.qr_data_uri} alt="One-time device pairing QR code" />
          <div>
            <span>PAIRING PIN</span>
            <strong>{pairing.pin}</strong>
            <small>One use · expires in five minutes</small>
          </div>
        </div>
      ) : (
        <p>Create a one-time credential for another device on this trusted network.</p>
      )}
      <div className="paneActions">
        <button className="textButton" onClick={onCreate}>
          <RefreshCw aria-hidden="true" /> {pairing ? 'New code' : 'Pair device'}
        </button>
        <button className="textButton danger" onClick={onRevoke}>
          <ShieldOff aria-hidden="true" /> Revoke remote
        </button>
      </div>
    </section>
  );
}

function Loading() {
  return (
    <main className="loadingPage">
      <img src="./pad-lattice-logo.svg" alt="Pad-Lattice" />
      <span>Opening surface…</span>
    </main>
  );
}

function emptySurface(): {view: SurfaceView; frame: VisualFrame} {
  const view: SurfaceView = {
    selected_state: null,
    frame: 0,
    sessions: [],
    available_actions: [],
    overflow_count: 0,
    activity_motion: false,
  };
  return {view, frame: compileVisualFrame(view)};
}
