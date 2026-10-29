import {useEffect, useMemo, useReducer, useRef, useState} from 'react';
import {BookOpen, Sun, Moon, Volume2, VolumeX} from 'lucide-react';
import {demoPrompt, demoSurfaceView, stateLabels} from './demo';
import {useDemoPlayback} from './demoPlayback';
import {DemoPlaybackControls} from './DemoPlaybackControls';
import {useAudioOutput} from './audio';
import {cueIndexAt, loadExperienceAssets, performanceCaptionAt, performanceFrame, type ExperienceAssets} from './experiences';
import {compileVisualFrame, tokenColor, emptySurface} from './surfaceModel';
import {createPlaygroundState, playgroundReducer, playgroundView} from './playground';
import {PlaygroundAgentPicker, PlaygroundControls, PlaygroundHistory} from './PlaygroundControls';
import type {ControlAction, ExperienceStateMessage} from './types';
import {VirtualSurface} from './VirtualSurface';
import {StreamDeckSurface, deckModel} from './StreamDeckSurface';
import {PageFrame, Loading, LoadFailure} from './AppFrame';
import {SessionList} from './SessionList';
import {ExperienceControls} from './ExperienceControls';

type PlaygroundSurface = 'virtual' | 'launchpad' | 'stream-deck' | 'stream-deck-xl' | 'stream-deck-neo';

export function PublicApp() {
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
    return requested === 'launchpad' || requested === 'stream-deck' || requested === 'stream-deck-xl' || requested === 'stream-deck-neo' ? requested : 'virtual';
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
    if (next === mode) return;
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
            onClick={() => chooseMode(item)}>{item === 'demo' ? 'Demo' : item === 'sandbox' ? 'Sandbox' : 'Show'}</button>)}
        </div>
        <div className="surfacePicker"><label htmlFor="playground-surface">Surface</label>
          <select id="playground-surface" value={surface} onChange={event => setSurface(event.target.value as PlaygroundSurface)}>
            <option value="virtual">Virtual Pad</option>
            <option value="launchpad">Launchpad Pro Mk1</option>
            <option value="stream-deck">Stream Deck</option>
            <option value="stream-deck-xl">Stream Deck XL</option>
            <option value="stream-deck-neo">Stream Deck Neo</option>
          </select>
        </div>
        <span>Browser simulation. No hardware or Codex connection required.</span>
      </nav>
      <div className={`workspace publicWorkspace ${mode === 'sandbox' ? 'sandboxWorkspace' : mode === 'demo' ? 'demoWorkspace' : ''}`}>
        {mode === 'sandbox' ? <PlaygroundControls state={sandbox} dispatch={sandboxDispatch} /> : null}
        <section className={`surfaceWorkspace ${mode === 'show' ? 'performanceWorkspace' : ''}`}>
          <div className="publicPadGroup">
            {mode === 'sandbox' ? <PlaygroundAgentPicker state={sandbox} dispatch={sandboxDispatch} grid={!surface.startsWith('stream-deck')} /> : null}
            {mode === 'demo' ? <DemoPlaybackControls playback={{...playback,
              toggle: () => {audio.stop(); playback.toggle();},
              replay: () => {audio.stop(); playback.replay();},
            }} onTry={() => chooseMode('sandbox')} /> : null}
            {mode === 'demo' ? <section className="narrative demoNarrative" aria-live="polite">
              <span>{prompt.eyebrow}</span>
              <h1>{prompt.title}</h1>
              <p>{prompt.detail}</p>
            </section> : null}
            {surface.startsWith('stream-deck') ? <StreamDeckSurface model={deckModel(surface)}
              view={view}
              showMode={mode === 'show'} performanceFrame={fullFrame}
              performanceAct={showAct} performanceCaption={showCaption}
              disabled={mode !== 'sandbox'}
              guidedAction={guidance?.action}
              guidedSlot={guidance?.slot}
              demonstration={mode === 'demo' ? playback.pointer : null}
              onAction={pressAction}
              onSelect={selectSession}
            /> : <VirtualSurface
              variant={surface === 'launchpad' ? 'launchpad' : 'virtual'}
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
              <strong>{selected ? `${surface.startsWith('stream-deck') ? 'Session' : 'Scene'} ${selected.slot + 1} / ${selected.label}` : 'No session selected'}</strong>
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
