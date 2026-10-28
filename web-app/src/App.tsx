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
  Check,
  X,
  Volume2,
  VolumeX,
  Maximize2,
  Minimize2,
  ArrowLeft,
  Unplug,
  Sun,
  Moon,
  ShieldAlert,
  CircleHelp,
  CircleAlert,
  Copy,
  MousePointer2,
  QrCode,
  Sparkles,
} from 'lucide-react';
import {
  demoPrompt,
  demoSurfaceView,
  stateLabels,
} from './demo';
import {useDemoPlayback} from './demoPlayback';
import {DemoPlaybackControls} from './DemoPlaybackControls';
import {useAudioOutput} from './audio';
import {
  cueIndexAt,
  loadExperienceAssets,
  performanceCaptionAt,
  performanceFrame,
  type ExperienceAssets,
} from './experiences';
import {useLiveSurface} from './live';
import {compileVisualFrame, isAgentState, tokenColor} from './surfaceModel';
import {AttentionView} from './AttentionView';
import {createPlaygroundState, playgroundReducer, playgroundView} from './playground';
import {PlaygroundAgentPicker, PlaygroundControls, PlaygroundHistory} from './PlaygroundControls';
import type {
  AgentState,
  ControlAction,
  ExperienceStateMessage,
  SessionView,
  SurfaceView,
  VisualFrame,
} from './types';
import {VirtualSurface} from './VirtualSurface';
import {StreamDeckSurface} from './StreamDeckSurface';
import {isDesktop, openProjectLink} from './desktop';
import {DesktopControls} from './DesktopControls';
import {ExploreMenu} from './ExploreMenu';
import {useLiveDemo} from './liveDemo';
import {PairingDialog} from './PairingDialog';
import {useDesktopPreference} from './useDesktopPreference';

type AppMode = 'loading' | 'demo' | 'live';
type PlaygroundSurface = 'virtual' | 'launchpad' | 'stream-deck';

export default function App() {
  const [mode, setMode] = useState<AppMode>('loading');
  useEffect(() => {
    if (isDesktop()) { setMode('live'); return; }
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
  const [surface, setSurface] = useState<PlaygroundSurface>(() => {
    const requested = new URLSearchParams(window.location.search).get('surface');
    return requested === 'launchpad' || requested === 'stream-deck' ? requested : 'virtual';
  });
  const [lightTheme, setLightTheme] = useState(() => {
    try { return localStorage.getItem('pad-lattice-playground-theme') === 'light'; }
    catch { return false; }
  });
  useEffect(() => {
    const theme = lightTheme ? 'light' : 'dark';
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('pad-lattice-playground-theme', theme); }
    catch { /* Theme switching also works when browser storage is blocked. */ }
    return () => { delete document.documentElement.dataset.theme; };
  }, [lightTheme]);
  const [sandbox, sandboxDispatch] = useReducer(playgroundReducer, undefined, () => createPlaygroundState());
  const [mode, setMode] = useState<'demo' | 'sandbox' | 'show'>('demo');
  const playback = useDemoPlayback(assets.demo, mode === 'demo');
  const demo = playback.state;
  const [showStatus, setShowStatus] = useState<'idle' | 'starting' | 'playing'>('idle');
  const [showElapsed, setShowElapsed] = useState(0);
  const showStartRef = useRef(0);
  const audio = useAudioOutput();
  const view = mode === 'show' ? emptySurface().view : mode === 'sandbox' ? playgroundView(sandbox) : demoSurfaceView(demo);
  const frame = useMemo(() => compileVisualFrame(view), [view]);
  const prompt = demoPrompt(demo);
  const guidance = mode === 'demo' ? playback.target : null;
  const showCueIndex = cueIndexAt(assets.performance, showElapsed);
  const showCue = assets.performance.cues[showCueIndex];
  const showAct = assets.performance.acts[showCue.act];
  const showCaption = performanceCaptionAt(assets.performance, showCueIndex);
  const showActive = mode === 'show' && showStatus !== 'idle';
  const selected = view.sessions.find((item) => item.selected);
  const selectSession = (slot: number) => {
    if (mode === 'sandbox') sandboxDispatch({type: 'select', slot, expectedRevision: sandbox.revision});
  };
  const pressAction = (action: ControlAction) => {
    if (mode === 'sandbox') sandboxDispatch({type: 'action', action, expectedRevision: sandbox.revision});
  };
  const fullFrame = mode === 'show' && showStatus === 'playing'
    ? performanceFrame(assets.performance, showCueIndex)
    : null;

  const playedCues = useRef({demo: 0, sandbox: 0});
  const cue = mode === 'sandbox' ? sandbox : demo;
  useEffect(() => {
    if (mode === 'show' || cue.audioSequence === playedCues.current[mode]) return;
    playedCues.current[mode] = cue.audioSequence;
    if (cue.audioCue) audio.playLiveCue(cue.audioCue, cue.audioSlot);
  }, [audio, cue.audioCue, cue.audioSequence, cue.audioSlot, mode]);

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
    if (mode !== 'show') return;
    if (showStatus === 'idle') { audio.syncExperience(null); return; }
    if (showStatus === 'starting') {
      const remaining = Math.max(0, showStartRef.current - performance.now());
      audio.syncExperience(publicShowState(assets, 'starting', 0, remaining));
    } else {
      audio.syncExperience(publicShowState(assets, 'playing', showElapsed));
    }
  }, [assets, audio, mode, showElapsed, showStatus]);

  const chooseMode = (next: 'demo' | 'sandbox' | 'show') => {
    if (next === mode || next === 'show' && surface === 'stream-deck') return;
    setShowStatus('idle');
    audio.stop();
    setMode(next);
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
    <PageFrame modeLabel="SIMULATION ONLY" connected={false} headerActions={
      <button className="textButton themeToggle" onClick={() => setLightTheme(!lightTheme)}
        title={lightTheme ? 'Switch to dark theme' : 'Switch to light theme'}
        aria-label={lightTheme ? 'Switch to dark theme' : 'Switch to light theme'}>
        {lightTheme ? <Moon aria-hidden="true" /> : <Sun aria-hidden="true" />}
      </button>
    }>
      {audio.error ? <p className="desktopError" role="alert">{audio.error}</p> : null}
      <nav className="publicToolbar" aria-label="Playground">
        <div className="modeSwitch" aria-label="Public experience">
          {(['demo', 'sandbox', 'show'] as const).map((item) => <button key={item}
            className={mode === item ? 'active' : ''} aria-pressed={mode === item}
            disabled={item === 'show' && surface === 'stream-deck'}
            title={item === 'show' && surface === 'stream-deck' ? 'Show requires Virtual Pad or Launchpad Pro' : undefined}
            onClick={() => chooseMode(item)}>{item === 'demo' ? 'Demo' : item === 'sandbox' ? 'Sandbox' : 'Show'}</button>)}
        </div>
        <div className="surfacePicker"><label htmlFor="playground-surface">Surface</label>
          <select id="playground-surface" value={surface} onChange={event => setSurface(event.target.value as PlaygroundSurface)}>
            <option value="virtual">Virtual Pad</option>
            <option value="launchpad">Launchpad Pro Mk1</option>
            <option value="stream-deck" disabled={mode === 'show'}>Stream Deck{mode === 'show' ? ' (Demo / Sandbox)' : ''}</option>
          </select>
        </div>
        <span>Browser simulation. No hardware or Codex connection required.</span>
      </nav>
      <div className={`workspace publicWorkspace ${mode === 'sandbox' ? 'sandboxWorkspace' : mode === 'demo' ? 'demoWorkspace' : ''}`}>
        {mode === 'sandbox' ? <PlaygroundControls state={sandbox} dispatch={sandboxDispatch} /> : null}
        <section className={`surfaceWorkspace ${mode === 'show' ? 'performanceWorkspace' : ''}`}>
          <div className="publicPadGroup">
            {mode === 'sandbox' ? <PlaygroundAgentPicker state={sandbox} dispatch={sandboxDispatch} grid={surface !== 'stream-deck'} /> : null}
            {mode === 'demo' ? <DemoPlaybackControls playback={{...playback,
              toggle: () => {audio.stop(); playback.toggle();},
              replay: () => {audio.stop(); playback.replay();},
            }} onTry={() => chooseMode('sandbox')} /> : null}
            {mode === 'demo' ? <section className="narrative demoNarrative" aria-live="polite">
              <span>{prompt.eyebrow}</span>
              <h1>{prompt.title}</h1>
              <p>{prompt.detail}</p>
            </section> : null}
            {surface === 'stream-deck' ? <StreamDeckSurface
              view={view}
              disabled={mode !== 'sandbox'}
              guidedAction={guidance?.action}
              guidedSlot={guidance?.slot}
              demonstration={mode === 'demo' ? playback.pointer : null}
              onAction={pressAction}
              onSelect={selectSession}
            /> : <VirtualSurface
              variant={surface}
              frame={frame}
              performanceFrame={fullFrame}
              showMode={mode === 'show'}
              performanceAct={showAct}
              performanceCaption={showCaption}
              guidedAction={guidance?.action}
              guidedSlot={guidance?.slot}
              demonstration={mode === 'demo' ? playback.pointer : null}
              view={view}
              disabled={mode !== 'sandbox'}
              onAction={pressAction}
              onSelect={selectSession}
            />}
            {mode !== 'show' ? <div className="selectedReadout" role="status">
              <span className="sessionAccent" aria-hidden="true" style={{background: selected ? tokenColor(`accent:${selected.accent}:selected`) : undefined}} />
              <strong>{selected ? `${surface === 'stream-deck' ? 'Session' : 'Scene'} ${selected.slot + 1} / ${selected.label}` : 'No session selected'}</strong>
              <span>{selected ? stateLabels[selected.state] : 'No action target'}</span>
            </div> : null}
            {surface !== 'virtual' ? <p className="hardwarePreviewNote">
              <a href={`https://mrueda.github.io/pad-lattice/docs/usage/${surface === 'launchpad' ? 'launchpad' : 'stream-deck'}`} target="_top">
                {surface === 'launchpad' ? 'Launchpad Pro Mk1' : 'Stream Deck (experimental)'}</a>
              {' '}&middot; Illustrated layout
            </p> : null}
          </div>
        </section>
        <aside className="contextPane">
          {mode === 'show' ? (
            <section className={`narrative ${mode === 'show' ? 'showNarrative' : ''}`} aria-live="polite">
              <span>{showActive ? showAct : 'Visual show'}</span>
              <h1>{showActive ? showCaption : assets.performance.title}</h1>
              <p>{showActive ? assets.performance.title : 'An audiovisual story across the complete pad surface.'}</p>
            </section>
          ) : null}

          {mode === 'show' ? (
            <ExperienceControls
              kind="show"
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
              title="SIMULATED AGENTS"
              sandbox={mode === 'sandbox'}
              readOnly={mode === 'demo'}
              guidedSlot={guidance?.slot}
              onSelect={selectSession}
              onState={(slot, state) => sandboxDispatch({type: 'set_state', slot, state})}
            />
          )}
          {mode === 'sandbox' ? <PlaygroundHistory state={sandbox} /> : null}

          <div className="paneActions">
            {mode !== 'show' ? (
              <button className="textButton" onClick={audio.toggle} aria-pressed={audio.enabled}>
                {audio.enabled ? <Volume2 aria-hidden="true" /> : <VolumeX aria-hidden="true" />}
                Sound {audio.enabled ? 'on' : 'off'}
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
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [pairingOpen, setPairingOpen] = useState(false);
  const [pairingKind, setPairingKind] = useState<'browser' | 'stream_deck'>('browser');
  const themePreference = useDesktopPreference('light_theme');
  useEffect(() => {
    if (!isDesktop()) return;
    document.documentElement.dataset.theme = themePreference.value ? 'light' : 'dark';
    return () => { delete document.documentElement.dataset.theme; };
  }, [themePreference.value]);
  const audio = useAudioOutput();
  const live = useLiveSurface(audio.playLiveCue);
  const [pin, setPin] = useState('');
  const [desktopExperience, setDesktopExperience] = useState<'demo' | 'show' | null>(null);
  const padPreference = useDesktopPreference('pad_focused');
  const setPadFocused = padPreference.save;
  const desktop = isDesktop();
  useEffect(() => {
    if (!desktop) return;
    const suppressMenu = (event: MouseEvent) => event.preventDefault();
    document.addEventListener('contextmenu', suppressMenu);
    return () => document.removeEventListener('contextmenu', suppressMenu);
  }, [desktop]);
  const exploring = !desktop || desktopExperience !== null;
  const empty = emptySurface();
  const view = live.surface?.view ?? empty.view;
  const demoActive = live.experience?.kind === 'demo'
    && ['starting', 'playing'].includes(live.experience.status);
  const agentsConnected = !demoActive && view.sessions.length > 0;
  const showMode = desktop ? desktopExperience === 'show' : live.experience?.kind === 'show'
    && ['starting', 'playing'].includes(live.experience.status);
  const demoGuidance = useLiveDemo(demoActive, live.experience, view);
  const padFocused = desktop && agentsConnected && padPreference.value;
  useEffect(() => {
    if (!padFocused) return;
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') setPadFocused(false); };
    window.addEventListener('keydown', escape);
    return () => window.removeEventListener('keydown', escape);
  }, [padFocused, setPadFocused]);
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
  useEffect(() => {
    if (agentsConnected || live.experience?.status === 'blocked'
        || live.experience?.reason === 'agents_connected') setDesktopExperience(null);
    else if (live.experience?.kind && ['starting', 'playing'].includes(live.experience.status)) {
      setDesktopExperience(live.experience.kind);
    }
  }, [agentsConnected, live.experience?.status, live.experience?.reason, live.experience?.kind]);
  const submitPin = (event: FormEvent) => {
    event.preventDefault();
    if (/^\d{6}$/.test(pin.replace(/\s/g, ''))) live.pair(pin);
  };
  const startDesktopExperience = (kind: 'demo' | 'show') => {
    if (agentsConnected || live.connection !== 'connected') return;
    live.stopExperience();
    setDesktopExperience(kind);
    live.startExperience(kind);
  };
  return (
    <PageFrame
      modeLabel={desktop && exploring ? 'SIMULATION' : 'CODEX CLI'}
      padOnly={padFocused}
      headerActions={<>
        <button className="textButton" onClick={audio.toggle} aria-pressed={audio.enabled}
          aria-label="Sound" title={audio.enabled ? 'Mute all sound' : 'Enable sound'}>
          {audio.enabled ? <Volume2 aria-hidden="true" /> : <VolumeX aria-hidden="true" />}
        </button>
        {desktop ? <ExploreMenu active={desktopExperience} disabled={agentsConnected || live.connection !== 'connected'} onStart={startDesktopExperience} /> : null}
        {!desktop && live.connection === 'connected' ? <button className="textButton" onClick={live.disconnect}
          aria-label="Disconnect this device" title="Disconnect this device"><Unplug aria-hidden="true" /></button> : null}
      </>}
      connected={live.connection === 'connected' && (!desktop || agentsConnected)}
      connectionLabel={desktop && !exploring
        ? live.connection !== 'connected' ? 'Disconnected'
          : agentsConnected ? `${view.sessions.length} ${view.sessions.length === 1 ? 'chat' : 'chats'} connected` : 'No chats connected'
        : undefined}>
      {desktop ? <div className="desktopSetup" hidden={padFocused}><DesktopControls audioEnabled={audio.enabled} onAudio={audio.toggle}
        showConversations={!exploring}
        settingsOpen={settingsOpen} onSettingsChange={setSettingsOpen}
        lightTheme={themePreference.value} onThemeChange={themePreference.save}
        onPairDevice={kind => {setPairingKind(kind); setPairingOpen(true); live.createPairing();}} /></div> : null}
      {desktop ? <PairingDialog open={pairingOpen} onClose={() => setPairingOpen(false)} title={pairingKind === 'stream_deck' ? 'Pair Stream Deck' : 'Pair a device'}>
        {live.pairing ? <PairingPanel kind={pairingKind} pairing={live.pairing} onCreate={live.createPairing} onRevoke={live.revokeRemote} />
          : <p role="status">{live.error || 'Creating pairing code...'}</p>}
      </PairingDialog> : null}
      {audio.error ? <p className="desktopError" role="alert">{audio.error}</p> : null}
      {padPreference.error ? <p className="desktopError" role="alert">{padPreference.error}</p> : null}
      {themePreference.error ? <p className="desktopError" role="alert">{themePreference.error}</p> : null}
      {live.connection !== 'connected' && live.connection !== 'pairing_required' ? <div className="connectionRecovery" role="status">
        <WifiOff aria-hidden="true" />
        <span>{live.paused ? live.error : live.connection === 'connecting' ? 'Connecting to Pad-Lattice...' : 'Desktop disconnected.'}</span>
        {live.connection === 'disconnected' ? <button className="textButton" onClick={live.reconnect}><RefreshCw />Reconnect</button> : null}
      </div> : null}
      {desktop && !settingsOpen && (exploring || agentsConnected) ? <div className="desktopViews">
        {exploring ? <div className="simulationBar"><span>SIMULATION: {desktopExperience === 'show' ? 'SHOW' : 'DEMO'}</span>
          <button className="textButton" onClick={() => {audio.stop(); live.stopExperience(); setDesktopExperience(null);}}><ArrowLeft /> Back to live pad</button></div> : null}
        <div className="desktopViewActions">
        {padFocused ? <button className="textButton" onClick={audio.toggle} aria-pressed={audio.enabled}
          aria-label="Sound" title={audio.enabled ? 'Mute all sound' : 'Enable sound'}>
          {audio.enabled ? <Volume2 aria-hidden="true" /> : <VolumeX aria-hidden="true" />}
        </button> : null}
        {agentsConnected ? <button className="textButton padFocusButton" title={padFocused ? 'Restore workspace' : 'Maximize pad'}
          aria-label={padFocused ? 'Restore workspace' : 'Maximize pad'} aria-pressed={padFocused}
          onClick={() => setPadFocused(!padFocused)}>{padFocused ? <Minimize2 /> : <Maximize2 />}</button> : null}
        </div>
      </div> : null}
      <div className={`workspace ${padFocused ? 'padFocusWorkspace' : ''} ${demoActive ? 'desktopDemoWorkspace' : ''}`} id={desktop ? 'desktop-workspace' : undefined}
        style={settingsOpen ? {display: 'none'} : undefined}>
        <section className={`surfaceWorkspace ${performance ? 'performanceWorkspace' : ''}`}>
          {demoActive && demoGuidance ? <div className="liveDemoCue" role="status">
            <MousePointer2 aria-hidden="true" /><div><small>YOUR TURN · SIMULATION</small>
              <strong>{demoGuidance.label}</strong><span>{demoGuidance.detail}</span></div>
          </div> : null}
          <VirtualSurface
            disabled={!live.controlsReady}
            frame={showMode ? empty.frame : frame}
            performanceFrame={performance}
            showMode={showMode}
            performanceAct={live.experience?.detail ?? 'VISUAL SHOW'}
            performanceCaption={live.experience?.caption ?? live.experience?.title ?? 'Ready'}
            view={showMode ? empty.view : view}
            guidedSlot={demoGuidance?.slot}
            guidedAction={demoGuidance?.action}
            onAction={live.sendAction}
            onSelect={live.selectSession}
          />
        </section>
        <aside className="contextPane">
          {desktop && exploring ? null : <ConnectionSummary state={live.connection} error={live.error} />}

          {live.connection === 'connected' && exploring && (desktop || live.admin) ? (
            <ExperienceControls
              kind={desktop ? desktopExperience : null}
              active={live.experience?.status === 'playing' || live.experience?.status === 'starting'}
              admin={live.admin}
              canStart={!agentsConnected}
              blockedReason={live.experience?.status === 'blocked' ? live.experience.reason : null}
              caption={live.experience?.caption}
              detail={live.experience?.detail}
              onStartDemo={desktop ? null : () => live.startExperience('demo')}
              onStartShow={desktop ? null : () => live.startExperience('show')}
              onStop={() => { audio.stop(); live.stopExperience(); }}
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

          {live.connection === 'connected' && !showMode ? (
            <>
              {desktop && !exploring ? <SelectedConversation view={view} disabled={!live.controlsReady} onAction={live.sendAction} /> : null}
              {desktop && !exploring && agentsConnected ? <AttentionView disabled={!live.controlsReady} revision={view.control_revision}>
                <SessionList sessions={view.sessions} readOnly={!live.controlsReady} onSelect={live.selectSession} title="Codex conversations" />
              </AttentionView> : <SessionList sessions={view.sessions} readOnly={!live.controlsReady} onSelect={live.selectSession}
                guidedSlot={demoGuidance?.slot}
                title={desktop ? (live.experience?.kind === 'demo' ? 'Demo sessions' : 'Codex conversations') : undefined} />}
            </>
          ) : null}

          {live.admin && !desktop ? (
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

function SelectedConversation({view, disabled, onAction}: {view: SurfaceView; disabled: boolean; onAction: (action: ControlAction) => void}) {
  const selected = view.sessions.find(session => session.selected);
  const actions = [
    {action: 'approve' as const, label: 'Approve', Icon: Check},
    {action: 'reject' as const, label: 'Reject', Icon: X},
    {action: 'stop' as const, label: 'Stop', Icon: Square},
    {action: 'retry' as const, label: 'Retry', Icon: RefreshCw},
  ];
  return <section className="selectedConversation" aria-label="Selected Codex conversation" aria-live="polite">
    <div className="sectionTitle"><span>SELECTED CONVERSATION</span>{selected ? <span>Scene {selected.slot + 1}</span> : null}</div>
    {selected ? <>
      <h2><i aria-hidden="true" style={{backgroundColor: tokenColor(`accent:${selected.accent}:selected`)}} />{selected.label}</h2>
      <p>{stateLabels[selected.state]}</p>
      <div className="conversationActions">
        {actions.filter(({action}) => view.available_actions.includes(action)).map(({action, label, Icon}) =>
          <button key={action} disabled={disabled} className={`textButton action-${action}`} onClick={() => onAction(action)}><Icon />{label}</button>)}
      </div>
    </> : <h2>{view.sessions.length ? 'No conversation selected' : 'No Codex conversation connected'}</h2>}
  </section>;
}

function ExperienceControls({
  kind = null,
  active,
  admin,
  canStart = true,
  audioEnabled = false,
  blockedReason = null,
  caption = null,
  detail = null,
  onAudio,
  onStartDemo = null,
  onStartShow,
  onStop,
}: {
  kind?: 'demo' | 'show' | null;
  active: boolean;
  admin: boolean;
  canStart?: boolean;
  audioEnabled?: boolean;
  blockedReason?: string | null;
  caption?: string | null;
  detail?: string | null;
  onAudio?: () => void;
  onStartDemo?: (() => void) | null;
  onStartShow: (() => void) | null;
  onStop: () => void;
}) {
  const AudioIcon = audioEnabled ? Volume2 : VolumeX;
  return (
    <section className="experiencePanel" aria-live="polite">
      <div className="sectionTitle"><span>{kind === 'demo' ? 'INTERACTIVE DEMO' : kind === 'show' ? 'VISUAL SHOW' : 'DEMO & SHOW'}</span><span>{active ? (kind === 'demo' ? 'IN PROGRESS' : 'PLAYING') : 'READY'}</span></div>
      {caption ? <p className="experienceCaption">{caption}</p> : null}
        {detail ? <p className="experienceDetail">{detail}</p> : null}
        {blockedReason ? <p className="experienceWarning">{blockedReason}</p> : null}
      <div className="experienceActions">
        {admin && !active && onStartDemo ? (
          <button className="primaryButton" disabled={!canStart} onClick={onStartDemo}>
            <Play aria-hidden="true" /> Start Demo
          </button>
        ) : null}
        {admin && !active && onStartShow ? (
          <button className="primaryButton" disabled={!canStart} onClick={onStartShow}>
            <Sparkles aria-hidden="true" /> Start Show
          </button>
        ) : null}
        {admin && active ? (
          <button className="primaryButton danger" onClick={onStop}>
            <Square aria-hidden="true" /> Stop
          </button>
        ) : null}
        {onAudio ? <button className="textButton" onClick={onAudio} aria-pressed={audioEnabled}>
          <AudioIcon aria-hidden="true" /> Sound {audioEnabled ? 'on' : 'off'}
        </button> : null}
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
  connectionLabel,
  padOnly = false,
  headerActions,
}: {
  children: React.ReactNode;
  modeLabel: string;
  connected: boolean;
  connectionLabel?: string;
  padOnly?: boolean;
  headerActions?: React.ReactNode;
}) {
  const [linkError, setLinkError] = useState('');
  const openLink = (event: React.MouseEvent, destination: 'docs' | 'github') => {
    if (!isDesktop()) return;
    event.preventDefault();
    setLinkError('');
    void openProjectLink(destination).catch((error: unknown) => setLinkError(String(error)));
  };
  return (
    <main className={`appPage${isDesktop() ? ' desktopApp' : ''}${padOnly ? ' padOnly' : ''}`}>
      <header className="appHeader">
        <a className="brand" href={isDesktop() ? 'https://mrueda.github.io/pad-lattice/' : '../'} target={isDesktop() ? '_blank' : '_top'} onClick={(event) => openLink(event, 'docs')}>
          <img src="./pad-lattice-logo.svg" alt="" />
          <span><strong>Pad-Lattice</strong><small>{isDesktop() ? 'Desktop' : 'Virtual Surface'}</small></span>
        </a>
        <div className="headerStatus">
          {headerActions}
          {connectionLabel ? <span className={`connectionBadge${connected ? ' connected' : ''}`} role="status">
            <span className={connected ? 'connectionDot connected' : 'connectionDot'} aria-hidden="true" />
            {connectionLabel}
          </span> : <span className={connected ? 'connectionDot connected' : 'connectionDot'} aria-hidden="true" />}
          <span>{modeLabel}</span>
        </div>
      </header>
      {children}
      {linkError ? <p className="desktopError" role="alert">{linkError}</p> : null}
      <footer className="appFooter">
        <span>A tactile visual language between people and AI agents.</span>
        <a href="https://github.com/mrueda/pad-lattice" target="_blank" rel="noreferrer" onClick={(event) => openLink(event, 'github')}>
          GitHub <ExternalLink aria-hidden="true" />
        </a>
      </footer>
    </main>
  );
}

const attentionIcons = {waiting_for_approval: ShieldAlert, waiting_for_reply: CircleHelp, error: CircleAlert};

function SessionState({state}: {state: AgentState}) {
  const Icon = state in attentionIcons ? attentionIcons[state as keyof typeof attentionIcons] : null;
  return <span className={`stateLabel ${Icon ? `attentionState ${state}` : ''}`}>
    {Icon ? <Icon aria-hidden="true" /> : null}{stateLabels[state]}
  </span>;
}

function SessionList({
  sessions,
  title = 'AGENT SCENES',
  sandbox = false,
  readOnly = false,
  guidedSlot = null,
  onSelect,
  onState,
}: {
  sessions: SessionView[];
  title?: string;
  sandbox?: boolean;
  readOnly?: boolean;
  guidedSlot?: number | null;
  onSelect: (slot: number) => void;
  onState?: (slot: number, state: AgentState) => void;
}) {
  return (
    <section className="sessionSection">
      <div className="sectionTitle"><span>{title}</span><span>{sessions.length}/8</span></div>
      <div className="sessionList">
        {sessions.map((session) => (
          <div
            className={`sessionRow ${session.selected ? 'selected' : ''} ${guidedSlot === session.slot ? 'guidedRow' : ''}`}
            key={session.slot}>
            <button disabled={readOnly} onClick={() => onSelect(session.slot)} title={`Select ${session.label}`} aria-pressed={session.selected}>
              <i aria-hidden="true" style={{backgroundColor: tokenColor(`accent:${session.accent}:selected`)}} />
              <span><strong>{session.label}</strong><small>Scene {session.slot + 1}</small></span>
            </button>
            {sandbox && onState ? (
              <select
                aria-label={`${session.label} state`}
                onChange={(event) => isAgentState(event.target.value) && onState(session.slot, event.target.value)}
                value={session.state}>
                {Object.entries(stateLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            ) : (
              <SessionState state={session.state} />
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
        <strong>{online ? 'Pad connected' : state.replace('_', ' ')}</strong>
        <small>{error ?? (online ? 'State and actions are synchronized.' : 'Waiting for the local bridge.')}</small>
      </span>
    </section>
  );
}

function PairingPanel({
  pairing,
  onCreate,
  onRevoke,
  kind = 'browser',
}: {
  pairing: ReturnType<typeof useLiveSurface>['pairing'];
  onCreate: () => void;
  onRevoke: () => void;
  kind?: 'browser' | 'stream_deck';
}) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const streamDeck = kind === 'stream_deck';
  const origin = pairing ? new URL(pairing.pairing_url).origin : '';
  useEffect(() => {setCopied(false); setCopyError(false);}, [origin]);
  async function copyAddress() {
    try {await navigator.clipboard.writeText(origin); setCopied(true); setCopyError(false);}
    catch {setCopyError(true);}
  }
  const pairingHost = pairing ? new URL(pairing.pairing_url).hostname : '';
  const localOnly = pairingHost === 'localhost' || pairingHost.startsWith('127.') || pairingHost === '[::1]';
  return (
    <section className="pairingPanel">
      <div className="sectionTitle"><span>PAIR A SURFACE</span><ShieldCheck aria-hidden="true" /></div>
      {pairing ? (
        <div className={`pairingContent${localOnly || streamDeck ? ' localPairing' : ''}`}>
          {!localOnly && !streamDeck ? <img src={pairing.qr_data_uri} alt="Scan to pair automatically without entering a PIN" /> : null}
          <div>
            {streamDeck ? <>
              <label className="pairingAddress">Pad-Lattice address
                <div><input readOnly aria-label="Pad-Lattice address" value={origin} onFocus={e => e.target.select()} />
                  <button className="textButton" aria-label={copied ? 'Address copied' : 'Copy address'} title={copied ? 'Address copied' : 'Copy address'} onClick={() => void copyAddress()}>
                    {copied ? <Check /> : <Copy />}</button></div>
              </label>
              {copyError ? <small role="status">Clipboard unavailable. Select and copy the address above.</small> : null}
            </> : null}
            {!localOnly && !streamDeck ? <><h3>Scan to pair</h3><small className="pairingScanNote">No PIN needed</small></> : null}
            <span>{streamDeck ? 'ONE-USE PIN' : localOnly ? 'LOCAL PAIRING PIN' : 'OR PAIR MANUALLY'}</span>
            {!localOnly && !streamDeck ? <small>{origin}</small> : null}
            <strong>{pairing.pin}</strong>
            {!localOnly && !streamDeck ? <small>Manual pairing PIN</small> : null}
            <small>One use · expires in five minutes</small>
            {localOnly && !streamDeck ? <small>{origin}</small> : null}
            {localOnly ? <small>{streamDeck ? 'Same computer only. No network setup needed.' : 'This computer only. Phone pairing is off.'}</small> : null}
            {streamDeck ? <small>Elgato software: select a Pad-Lattice key, enter address and PIN, then Pair. All keys share the connection.</small> : null}
          </div>
        </div>
      ) : (
        <p>Pair Stream Deck on this computer, or enable network pairing in Settings for another device.</p>
      )}
      <div className="paneActions">
        <button className="textButton" onClick={onCreate}>
          {pairing ? <RefreshCw aria-hidden="true" /> : <QrCode aria-hidden="true" />} {pairing ? 'New code' : 'Pair device'}
        </button>
        <button className="textButton danger" onClick={onRevoke}>
          <ShieldOff aria-hidden="true" /> Revoke paired devices
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
