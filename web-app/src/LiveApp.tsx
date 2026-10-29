import {useEffect, useState, type FormEvent} from 'react';
import {Link2, RefreshCw, WifiOff, Volume2, VolumeX, Maximize2, Minimize2, ArrowLeft, Unplug, MousePointer2, Grid3X3, LayoutGrid} from 'lucide-react';
import {useAudioOutput} from './audio';
import {useLiveSurface} from './live';
import {emptySurface} from './surfaceModel';
import {AttentionView} from './AttentionView';
import {VirtualSurface} from './VirtualSurface';
import {StreamDeckSurface, deckModel} from './StreamDeckSurface';
import {isDesktop} from './desktop';
import {DesktopControls} from './DesktopControls';
import {ExploreMenu} from './ExploreMenu';
import {useLiveDemo} from './liveDemo';
import {PairingDialog} from './PairingDialog';
import {useDesktopPreference, useSurfacePreference} from './useDesktopPreference';
import {DemoCodexQuestion, LiveCodexQuestion} from './CodexQuestion';
import {ApprovalContext} from './ApprovalContext';
import {PageFrame} from './AppFrame';
import {SessionList, SelectedConversation} from './SessionList';
import {ExperienceControls} from './ExperienceControls';
import {ConnectionSummary, PairingPanel} from './ConnectionPanels';

export function LiveApp() {
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
  const deckPreference = useSurfacePreference();
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
  const selectedSession = view.sessions.find(session => session.selected);
  const selectedSlot = selectedSession?.slot ?? null;
  const questionEnabled = live.controlsReady && view.selected_state === 'waiting_for_reply'
    && (desktop ? !exploring && !settingsOpen : !demoActive && !showMode);
  const approvalEnabled = desktop && !exploring && !settingsOpen && live.controlsReady
    && view.selected_state === 'waiting_for_approval';
  const deckView = desktop && deckPreference.value !== 'grid';
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
          : agentsConnected ? `${view.sessions.length} ${view.sessions.length === 1 ? 'chat' : 'chats'} on pad` : 'No chats connected'
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
      {deckPreference.error ? <p className="desktopError" role="alert">{deckPreference.error}</p> : null}
      {live.connection !== 'connected' && live.connection !== 'pairing_required' ? <div className="connectionRecovery" role="status">
        <WifiOff aria-hidden="true" />
        <span>{live.paused ? live.error : live.connection === 'connecting' ? 'Connecting to Pad-Lattice...' : 'Desktop disconnected.'}</span>
        {live.connection === 'disconnected' ? <button className="textButton" onClick={live.reconnect}><RefreshCw />Reconnect</button> : null}
      </div> : null}
      {desktop && !settingsOpen ? <div className="desktopViews">
        {exploring ? <div className="simulationBar"><span>SIMULATION: {desktopExperience === 'show' ? 'SHOW' : 'DEMO'}</span>
          <button className="textButton" onClick={() => {audio.stop(); live.stopExperience(); setDesktopExperience(null);}}><ArrowLeft /> Back to live pad</button></div> : null}
        <div className="desktopViewActions">
        <div className="desktopSurfaceSelector" role="group" aria-label="Surface layout">
          <button type="button" aria-pressed={!deckView} onClick={() => deckPreference.save('grid')}><Grid3X3 aria-hidden="true" /> Grid</button>
          <button type="button" aria-pressed={deckPreference.value === 'stream-deck'} title="Stream Deck 15-key layout"
            onClick={() => deckPreference.save('stream-deck')}><LayoutGrid aria-hidden="true" /> Stream Deck</button>
          <button type="button" aria-label="Stream Deck XL" aria-pressed={deckPreference.value === 'stream-deck-xl'} title="Stream Deck XL layout"
            onClick={() => deckPreference.save('stream-deck-xl')}>XL</button>
          <button type="button" aria-label="Stream Deck Neo" aria-pressed={deckPreference.value === 'stream-deck-neo'} title="Stream Deck Neo layout"
            onClick={() => deckPreference.save('stream-deck-neo')}>Neo</button>
        </div>
        {padFocused ? <button className="textButton" onClick={audio.toggle} aria-pressed={audio.enabled}
          aria-label="Sound" title={audio.enabled ? 'Mute all sound' : 'Enable sound'}>
          {audio.enabled ? <Volume2 aria-hidden="true" /> : <VolumeX aria-hidden="true" />}
        </button> : null}
        {agentsConnected ? <button className="textButton padFocusButton" title={padFocused ? 'Restore workspace' : 'Maximize pad'}
          aria-label={padFocused ? 'Restore workspace' : 'Maximize pad'} aria-pressed={padFocused}
          onClick={() => setPadFocused(!padFocused)}>{padFocused ? <Minimize2 /> : <Maximize2 />}</button> : null}
        </div>
      </div> : null}
      {!desktop && questionEnabled ? <div className="browserQuestionBar">
        <LiveCodexQuestion slot={selectedSlot} revision={view.control_revision ?? null} enabled sessionName={selectedSession?.label} request={live.questionRequest} />
      </div> : null}
      <div className={`workspace ${padFocused ? 'padFocusWorkspace' : ''} ${demoActive ? 'desktopDemoWorkspace' : ''}`} id={desktop ? 'desktop-workspace' : undefined}
        style={settingsOpen ? {display: 'none'} : undefined}>
        <section className={`surfaceWorkspace ${performance ? 'performanceWorkspace' : ''}`}>
          {padFocused && questionEnabled ? <LiveCodexQuestion slot={selectedSlot} revision={view.control_revision ?? null} enabled sessionName={selectedSession?.label} /> : null}
          {padFocused && approvalEnabled ? <ApprovalContext slot={selectedSlot} revision={view.control_revision ?? null} enabled /> : null}
          {demoActive && demoGuidance ? <div className="liveDemoCue" role="status">
            <MousePointer2 aria-hidden="true" /><div><small>YOUR TURN · SIMULATION</small>
            <strong>{demoGuidance.label}</strong><span>{deckView
              ? demoGuidance.event === 'select' ? `Session key ${Number(demoGuidance.slot) + 1}` : `${demoGuidance.action === 'approve' ? 'Approve' : 'Reject'} key for the selected session`
              : demoGuidance.detail}</span></div>
          </div> : null}
          {deckView ? <StreamDeckSurface live includeRetry model={deckModel(deckPreference.value)} view={view} disabled={!live.controlsReady}
            showMode={showMode} performanceFrame={performance} performanceAct={live.experience?.detail} performanceCaption={live.experience?.caption ?? live.experience?.title}
            guidedSlot={demoGuidance?.slot} guidedAction={demoGuidance?.action}
            onAction={live.sendAction} onSelect={live.selectSession} /> : <VirtualSurface
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
          />}
        </section>
        <aside className="contextPane">
          {desktop ? null : <ConnectionSummary state={live.connection} error={live.error} />}

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
              {desktop && !exploring ? <SelectedConversation view={view} disabled={!live.controlsReady} onAction={live.sendAction}>
                {!padFocused && approvalEnabled ? <ApprovalContext slot={selectedSlot} revision={view.control_revision ?? null} enabled /> : null}
              </SelectedConversation> : null}
              {desktop && !padFocused && questionEnabled ? <LiveCodexQuestion slot={selectedSlot} revision={view.control_revision ?? null} enabled sessionName={selectedSession?.label} /> : null}
              {desktop && demoActive ? <DemoCodexQuestion /> : null}
              {desktop && !exploring && agentsConnected ? <AttentionView disabled={!live.controlsReady} revision={view.control_revision}>
                <SessionList sessions={view.sessions} readOnly={!live.controlsReady} onSelect={live.selectSession} title="Codex conversations" />
              </AttentionView> : !desktop || demoActive ? <SessionList sessions={view.sessions} readOnly={!live.controlsReady} onSelect={live.selectSession}
                guidedSlot={demoGuidance?.slot}
                title={desktop ? 'Demo sessions' : undefined} /> : null}
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
