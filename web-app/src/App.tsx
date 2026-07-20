import {useEffect, useMemo, useReducer, useRef, useState, type FormEvent} from 'react';
import {
  BookOpen,
  ExternalLink,
  Link2,
  MonitorSmartphone,
  Play,
  RefreshCw,
  ShieldCheck,
  ShieldOff,
  Wifi,
  WifiOff,
  Square,
  Volume2,
  VolumeX,
} from 'lucide-react';
import {
  createDemoState,
  demoGuidance,
  demoPrompt,
  demoReducer,
  demoSurfaceView,
  stateLabels,
  validDemoState,
  type DemoGuidance,
} from './demo';
import {useAudioOutput} from './audio';
import {
  cueIndexAt,
  loadExperienceAssets,
  performanceCaptionAt,
  performanceFrame,
  type ExperienceAssets,
} from './experiences';
import {useLiveSurface} from './live';
import {compileVisualFrame, tokenColor} from './surfaceModel';
import type {
  AgentState,
  ControlAction,
  ExperienceStateMessage,
  SessionView,
  SurfaceView,
  VisualFrame,
} from './types';
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
  const [assets, setAssets] = useState<ExperienceAssets | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    loadExperienceAssets().then(setAssets).catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : 'Experience assets are unavailable.');
    });
  }, []);
  if (error) return <LoadFailure message={error} />;
  if (!assets) return <Loading />;
  return <PublicExperienceApp assets={assets} />;
}

function PublicExperienceApp({assets}: {assets: ExperienceAssets}) {
  const [demo, dispatch] = useReducer(demoReducer, assets.demo, createDemoState);
  const [mode, setMode] = useState<'demo' | 'sandbox' | 'show'>('demo');
  const [showStatus, setShowStatus] = useState<'idle' | 'starting' | 'playing'>('idle');
  const [showElapsed, setShowElapsed] = useState(0);
  const showStartRef = useRef(0);
  const audio = useAudioOutput();
  const view = demoSurfaceView(demo);
  const frame = useMemo(() => compileVisualFrame(view), [view]);
  const prompt = demoPrompt(demo);
  const guidance = mode === 'demo' ? demoGuidance(demo) : null;
  const showCueIndex = cueIndexAt(assets.performance, showElapsed);
  const showCue = assets.performance.cues[showCueIndex];
  const showAct = assets.performance.acts[showCue.act];
  const showCaption = performanceCaptionAt(assets.performance, showCueIndex);
  const showActive = mode === 'show' && showStatus !== 'idle';
  const fullFrame = mode === 'show' && showStatus === 'playing'
    ? performanceFrame(assets.performance, showCueIndex)
    : null;

  useEffect(() => {
    if (mode !== 'show') audio.playCue(demo.audioCue, demo.audioSlot, demo.audioSequence);
  }, [audio, demo.audioCue, demo.audioSequence, demo.audioSlot, mode]);

  useEffect(() => {
    if (showStatus === 'idle') return;
    const timer = window.setInterval(() => {
      const now = performance.now();
      if (now < showStartRef.current) return;
      if (showStatus === 'starting') setShowStatus('playing');
      const elapsed = now - showStartRef.current;
      if (elapsed >= assets.performance.duration_ms) {
        setShowElapsed(assets.performance.duration_ms - 1);
        setShowStatus('idle');
        audio.stop();
      } else {
        setShowElapsed(elapsed);
      }
    }, 30);
    return () => window.clearInterval(timer);
  }, [assets.performance.duration_ms, audio, showStatus]);

  useEffect(() => {
    if (mode !== 'show' || showStatus === 'idle') return;
    if (showStatus === 'starting') {
      const remaining = Math.max(0, showStartRef.current - performance.now());
      audio.syncExperience(publicShowState(assets, 'starting', 0, remaining));
    } else {
      audio.syncExperience(publicShowState(assets, 'playing', showElapsed));
    }
  }, [assets, audio, mode, showElapsed, showStatus]);

  const chooseMode = (next: 'demo' | 'sandbox' | 'show') => {
    if (next !== 'show') {
      setShowStatus('idle');
      audio.stop();
      dispatch({type: 'mode', mode: next});
    }
    setMode(next);
  };
  const resetSimulation = () => {
    dispatch({type: 'mode', mode: mode === 'sandbox' ? 'sandbox' : 'demo'});
  };
  const startShow = () => {
    const delay = 500;
    setShowElapsed(0);
    showStartRef.current = performance.now() + delay;
    setShowStatus('starting');
  };
  const stopShow = () => {
    setShowStatus('idle');
    audio.stop();
  };

  return (
    <PageFrame modeLabel="PUBLIC SIMULATION" connected>
      <div className="workspace">
        <section className={`surfaceWorkspace ${mode === 'show' ? 'performanceWorkspace' : ''}`}>
          <VirtualSurface
            frame={frame}
            performanceFrame={fullFrame}
            performanceAct={showAct}
            performanceCaption={showCaption}
            guidedAction={guidance?.action}
            guidedSlot={guidance?.slot}
            view={view}
            onAction={(action) => dispatch({type: 'action', action})}
            onSelect={(slot) => dispatch({type: 'select', slot})}
          />
        </section>
        <aside className="contextPane">
          <div className="modeSwitch" aria-label="Public experience">
            <button
              className={mode === 'demo' ? 'active' : ''}
              onClick={() => chooseMode('demo')}>Demo</button>
            <button
              className={mode === 'sandbox' ? 'active' : ''}
              onClick={() => chooseMode('sandbox')}>Sandbox</button>
            <button
              className={mode === 'show' ? 'active' : ''}
              onClick={() => chooseMode('show')}>Show</button>
          </div>

          <section className={`narrative ${mode === 'show' ? 'showNarrative' : ''}`} aria-live="polite">
            <span>{mode === 'show' ? (showActive ? showAct : 'Visual show') : prompt.eyebrow}</span>
            <h1>{mode === 'show' ? (showActive ? showCaption : assets.performance.title) : prompt.title}</h1>
            <p>{mode === 'show'
              ? (showActive ? assets.performance.title : 'An audiovisual story across the complete pad surface.')
              : prompt.detail}</p>
          </section>

          {guidance ? <GuidedAction guidance={guidance} /> : null}

          {mode === 'show' ? (
            <ExperienceControls
              active={showStatus !== 'idle'}
              admin
              audioEnabled={audio.enabled}
              onAudio={audio.toggle}
              onStartShow={startShow}
              onStop={stopShow}
            />
          ) : (
            <SessionList
              sessions={view.sessions}
              sandbox={demo.mode === 'sandbox'}
              guidedSlot={guidance?.slot}
              onSelect={(slot) => dispatch({type: 'select', slot})}
              onState={(slot, state) => dispatch({type: 'set_state', slot, state})}
            />
          )}

          <div className="paneActions">
            {mode !== 'show' ? (
              <button className="textButton" onClick={audio.toggle} aria-pressed={audio.enabled}>
                {audio.enabled ? <Volume2 aria-hidden="true" /> : <VolumeX aria-hidden="true" />}
                Sound {audio.enabled ? 'on' : 'off'}
              </button>
            ) : null}
            {mode !== 'show' ? (
              <button className="textButton" onClick={resetSimulation}>
                <RefreshCw aria-hidden="true" />
                {mode === 'sandbox' ? 'Reset sandbox' : 'Restart demo'}
              </button>
            ) : null}
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
  const audio = useAudioOutput();
  const [pin, setPin] = useState('');
  const empty = emptySurface();
  const view = live.surface?.view ?? empty.view;
  const frame = live.surface?.visual_frame ?? empty.frame;
  const performance = live.experience?.kind === 'show'
    && ['starting', 'playing'].includes(live.experience.status)
    ? live.performanceFrame
    : null;
  useEffect(() => {
    audio.syncExperience(live.experience);
    if (live.experience?.kind === 'demo') {
      audio.playCue(
        live.experience.audio_cue,
        live.experience.audio_slot,
        live.experience.audio_sequence,
      );
    }
  }, [audio, live.experience]);
  const submitPin = (event: FormEvent) => {
    event.preventDefault();
    if (/^\d{6}$/.test(pin.replace(/\s/g, ''))) live.pair(pin);
  };
  return (
    <PageFrame
      modeLabel="LIVE CODEX"
      connected={live.connection === 'connected'}>
      <div className="workspace">
        <section className={`surfaceWorkspace ${performance ? 'performanceWorkspace' : ''}`}>
          <VirtualSurface
            disabled={live.connection !== 'connected'}
            frame={frame}
            performanceFrame={performance}
            performanceAct={live.experience?.detail}
            performanceCaption={live.experience?.caption}
            view={view}
            onAction={live.sendAction}
            onSelect={live.selectSession}
          />
        </section>
        <aside className="contextPane">
          <ConnectionSummary state={live.connection} error={live.error} />

          {live.connection === 'connected' ? (
            <ExperienceControls
              active={live.experience?.status === 'playing' || live.experience?.status === 'starting'}
              admin={live.admin}
              audioEnabled={audio.enabled}
              blockedReason={live.experience?.status === 'blocked' ? live.experience.reason : null}
              caption={live.experience?.caption}
              detail={live.experience?.detail}
              onAudio={audio.toggle}
              onStartDemo={() => live.startExperience('demo')}
              onStartShow={() => live.startExperience('show')}
              onStop={live.stopExperience}
            />
          ) : null}

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

function ExperienceControls({
  active,
  admin,
  audioEnabled,
  blockedReason = null,
  caption = null,
  detail = null,
  onAudio,
  onStartDemo = null,
  onStartShow,
  onStop,
}: {
  active: boolean;
  admin: boolean;
  audioEnabled: boolean;
  blockedReason?: string | null;
  caption?: string | null;
  detail?: string | null;
  onAudio: () => void;
  onStartDemo?: (() => void) | null;
  onStartShow: () => void;
  onStop: () => void;
}) {
  const AudioIcon = audioEnabled ? Volume2 : VolumeX;
  return (
    <section className="experiencePanel" aria-live="polite">
      <div className="sectionTitle"><span>EXPERIENCES</span><span>{active ? 'PLAYING' : 'READY'}</span></div>
      {caption ? <p className="experienceCaption">{caption}</p> : null}
        {detail ? <p className="experienceDetail">{detail}</p> : null}
        {blockedReason ? <p className="experienceWarning">{blockedReason}</p> : null}
      <div className="experienceActions">
        {admin && !active && onStartDemo ? (
          <button className="primaryButton" onClick={onStartDemo}>
            <Play aria-hidden="true" /> Start Demo
          </button>
        ) : null}
        {admin && !active ? (
          <button className="primaryButton" onClick={onStartShow}>
            <Play aria-hidden="true" /> Start Show
          </button>
        ) : null}
        {admin && active ? (
          <button className="primaryButton danger" onClick={onStop}>
            <Square aria-hidden="true" /> Stop
          </button>
        ) : null}
        <button className="textButton" onClick={onAudio} aria-pressed={audioEnabled}>
          <AudioIcon aria-hidden="true" /> Sound {audioEnabled ? 'on' : 'off'}
        </button>
      </div>
    </section>
  );
}

function publicShowState(
  assets: ExperienceAssets,
  status: 'starting' | 'playing',
  elapsedMs: number,
  startDelayMs = 0,
): ExperienceStateMessage {
  const cueIndex = cueIndexAt(assets.performance, elapsedMs);
  const cue = assets.performance.cues[cueIndex];
  return {
    protocol: 1,
    type: 'experience_state',
    status,
    kind: 'show',
    title: assets.performance.title,
    cue_index: cueIndex,
    caption: performanceCaptionAt(assets.performance, cueIndex),
    detail: assets.performance.acts[cue.act],
    elapsed_ms: elapsedMs,
    duration_ms: assets.performance.duration_ms,
    tempo: 1,
    audio_asset: `experiences/${assets.performance.audio.asset}`,
    audio_cue: null,
    audio_slot: null,
    audio_sequence: 0,
    start_delay_ms: startDelayMs,
    reason: null,
  };
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
  guidedSlot = null,
  onSelect,
  onState,
}: {
  sessions: SessionView[];
  sandbox?: boolean;
  guidedSlot?: number | null;
  onSelect: (slot: number) => void;
  onState?: (slot: number, state: AgentState) => void;
}) {
  return (
    <section className="sessionSection">
      <div className="sectionTitle"><span>AGENT SCENES</span><span>{sessions.length}/8</span></div>
      <div className="sessionList">
        {sessions.map((session) => (
          <div
            className={`sessionRow ${session.selected ? 'selected' : ''} ${guidedSlot === session.slot ? 'guidedRow' : ''}`}
            key={session.slot}>
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

function GuidedAction({guidance}: {guidance: DemoGuidance}) {
  return (
    <section className="guideCallout" aria-label="Next action">
      <span>NEXT ACTION</span>
      <strong>{guidance.title}</strong>
      <small>{guidance.detail}</small>
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

function LoadFailure({message}: {message: string}) {
  return (
    <main className="loadingPage">
      <img src="./pad-lattice-logo.svg" alt="Pad-Lattice" />
      <span>{message}</span>
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
