import {useCallback, useEffect, useRef, useState, type KeyboardEvent} from 'react';
import {BookOpen, Download, Cable, QrCode, Grid2X2, FolderOpen, Settings, RefreshCw, RotateCw, Plug, Unplug, Wifi, WifiOff, ArrowLeft, Sun, Moon, MonitorSmartphone, SlidersHorizontal, Terminal, Info, CheckCircle2, CircleAlert, Stethoscope} from 'lucide-react';
import {choosePath, desktopRequest, openProjectLink} from './desktop';
import {OpenConversations} from './OpenConversations';
import {PairedDevices, usePairedDevices} from './PairedDevices';
import {About} from './About';
import {HardwareTest} from './HardwareTest';
import {DeviceIllustration} from './DeviceIllustration';

const settingsPages = [
  {id: 'general', label: 'Appearance & sound', Icon: SlidersHorizontal},
  {id: 'devices', label: 'Devices', Icon: Cable},
  {id: 'codex', label: 'Codex', Icon: Terminal},
  {id: 'about', label: 'About', Icon: Info},
] as const;

const devicePages = [
  {id: 'browser', label: 'Browsers', Icon: MonitorSmartphone},
  {id: 'midi', label: 'MIDI controllers', Icon: Plug},
  {id: 'stream_deck', label: 'Stream Deck', Icon: Grid2X2},
] as const;
type DevicePage = typeof devicePages[number]['id'];

function navigateTabs(event: KeyboardEvent<HTMLDivElement>) {
  if (!['ArrowDown', 'ArrowUp', 'ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
  event.preventDefault();
  const tabs = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]'));
  const current = tabs.indexOf(document.activeElement as HTMLButtonElement);
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1
    : (current + (['ArrowRight', 'ArrowDown'].includes(event.key) ? 1 : -1) + tabs.length) % tabs.length;
  tabs[next]?.click(); tabs[next]?.focus();
}

interface Status {
  version: string;
  settings: {codex?: string; midi_profile?: string; midi_input?: string; midi_output?: string;
    pairing_host?: string; pairing_port?: string; pairing_advertise_host?: string; share_browser_questions?: boolean};
  inputs: string[];
  outputs: string[];
  profiles: Array<{id: string; status: string}>;
  midi: string | null;
  midi_error: string | null;
  lan_host: string;
  network_url: string | null;
  port: number;
}
interface Codex {available: boolean; version?: string; tested?: boolean; tested_version: string; error?: string}

export function DesktopControls({audioEnabled, onAudio, settingsOpen, onSettingsChange, onPairDevice, lightTheme, onThemeChange, showConversations = true}: {
  showConversations?: boolean;
  audioEnabled: boolean;
  onAudio: () => void;
  settingsOpen: boolean;
  onSettingsChange: (open: boolean) => void;
  onPairDevice: (kind: 'browser' | 'stream_deck') => void;
  lightTheme: boolean;
  onThemeChange: (light: boolean) => void;
}) {
  const [status, setStatus] = useState<Status | null>(null);
  const paired = usePairedDevices();
  const connectedDevices = paired.devices?.filter(device => device.connected).length ?? 0;
  const [page, setPage] = useState<string>('general');
  const [devicePage, setDevicePage] = useState<DevicePage>('browser');
  const [codex, setCodex] = useState<Codex | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [hardwareTesting, setHardwareTesting] = useState(false);
  const [codexPath, setCodexPath] = useState('');
  const [profile, setProfile] = useState('');
  const [input, setInput] = useState('');
  const [output, setOutput] = useState('');
  const [lan, setLan] = useState('');
  const [sharedNetwork, setSharedNetwork] = useState(false);
  const [advertiseHost, setAdvertiseHost] = useState('');
  const [pairingPort, setPairingPort] = useState('8001');
  const [networkError, setNetworkError] = useState('');
  const [networkBusy, setNetworkBusy] = useState(false);
  const [checkingCodex, setCheckingCodex] = useState(false);
  const settingsBack = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!settingsOpen) return;
    const opener = document.activeElement;
    settingsBack.current?.focus();
    return () => { if (opener instanceof HTMLElement && opener.isConnected) opener.focus(); };
  }, [settingsOpen]);
  const refresh = useCallback(async () => {
    const next = await desktopRequest<Status>('status');
    setStatus(next);
    return next;
  }, []);
  useEffect(() => {
    refresh().then((next) => {
      setCodexPath(next.settings.codex ?? '');
      setProfile(next.settings.midi_profile ?? '');
      setInput(next.settings.midi_input ?? '');
      setOutput(next.settings.midi_output ?? '');
      setLan(next.lan_host !== '127.0.0.1' ? next.lan_host : next.settings.pairing_host ?? '');
      setPairingPort(next.settings.pairing_port || '8001');
      setAdvertiseHost(next.settings.pairing_advertise_host ?? '');
      setSharedNetwork(Boolean(next.settings.pairing_advertise_host));
      if (next.network_url) {
        const url = new URL(next.network_url);
        setPairingPort(url.port || '80');
        if (url.hostname !== next.lan_host) {
          setSharedNetwork(true);
          setAdvertiseHost(url.hostname);
        }
      }
      return desktopRequest<Codex>('inspect_codex');
    }).then(setCodex).catch((reason) => setError(String(reason)));
    let disposed = false;
    let cleanup: (() => void) | undefined;
    import('@tauri-apps/api/event').then(async ({listen}) => {
      const unlisten = await listen<{error?: string}>('pad-lattice-device', ({payload}) => {
        if (payload.error) setError(payload.error);
        refresh().catch((reason) => setError(String(reason)));
      });
      if (disposed) unlisten(); else cleanup = unlisten;
    });
    return () => { disposed = true; cleanup?.(); };
  }, [refresh]);
  const run = async (work: () => Promise<unknown>) => {
    setBusy(true); setError('');
    try { await work(); } catch (reason) { setError(String(reason)); } finally { setBusy(false); }
  };
  const savePreferences = async (values: Record<string, string>, inspect = false) => {
    try {
      await desktopRequest('settings', values);
      if (inspect) setCodex(await desktopRequest<Codex>('inspect_codex'));
    } catch (reason) { setError(`Could not save preferences: ${String(reason)}`); }
  };
  const checkCodex = async () => {
    setCheckingCodex(true); setError('');
    try {
      setCodex(await desktopRequest<Codex>('inspect_codex', {codex: codexPath}));
    } catch (reason) {
      setCodex({available: false, tested_version: '', error: String(reason)});
    } finally { setCheckingCodex(false); }
  };
  const openCodex = () => {setPage('codex'); onSettingsChange(true);};
  const openDiagnostics = () => {setPage('about'); onSettingsChange(true);};
  const enableNetwork = async () => {
    setNetworkError('');
    if (!lan.trim()) {
      setNetworkError(sharedNetwork ? 'Enter the VM IPv4 address.' : 'Enter this computer\'s IPv4 address.');
      return;
    }
    if (sharedNetwork && !advertiseHost.trim()) {
      setNetworkError('Enter the Mac / host IPv4 address.');
      return;
    }
    const port = Number(pairingPort);
    if (!Number.isInteger(port) || port < 1 || port > 65535) {
      setNetworkError('Enter a port between 1 and 65535.');
      return;
    }
    setNetworkBusy(true);
    try {
      const next = await desktopRequest<Status>('lan', {host: lan.trim(), port,
        advertise_host: sharedNetwork ? advertiseHost.trim() : null});
      setStatus(next);
      onPairDevice(devicePage === 'stream_deck' ? 'stream_deck' : 'browser');
    } catch (reason) {
      setNetworkError(String(reason));
    } finally {
      setNetworkBusy(false);
    }
  };
  const openDevices = (kind: DevicePage) => {
    setDevicePage(kind); setPage('devices'); onSettingsChange(true);
  };
  return (
    <section className="desktopControls">
      <div className="desktopToolbar">
        <div className="desktopConnections">
          <button className="connectionLink desktopRuntime" title="Codex connection settings" onClick={openCodex}>
            <Terminal aria-hidden="true" />{!codex ? 'Checking Codex CLI...' : codex.available ? `Codex CLI ${codex.version ?? 'available'}` : 'Codex CLI setup required'}</button>
          <button className={`connectionLink${status?.midi && !status.midi_error ? ' online' : ''}`}
            title={status?.midi_error || status?.midi || 'MIDI controller settings'}
            onClick={() => openDevices('midi')}><Plug aria-hidden="true" />
            MIDI: {!status ? 'checking...' : status.midi_error ? 'unavailable' : status.midi ? 'connected' : 'not connected'}</button>
          <button className={`connectionLink${connectedDevices && !paired.error ? ' online' : ''}`}
            title="View paired devices" onClick={() => openDevices(paired.devices?.some(device => device.kind === 'stream_deck')
              && !paired.devices?.some(device => device.kind === 'browser') ? 'stream_deck' : 'browser')}>
            <MonitorSmartphone aria-hidden="true" />{paired.error ? 'Device status unavailable' : !paired.devices ? 'Checking devices...'
              : `${connectedDevices} ${connectedDevices === 1 ? 'device' : 'devices'} connected`}</button>
          {status?.network_url ? <span title={status.network_url}><Wifi aria-hidden="true" />Network enabled</span> : null}
        </div>
        <div className="desktopActions">
          {!settingsOpen ? <button className="textButton" onClick={() => openDevices('browser')}><QrCode aria-hidden="true" /> Pair device</button> : null}
          <button className="textButton" title="Settings" aria-label="Settings" aria-expanded={settingsOpen} onClick={() => onSettingsChange(!settingsOpen)}><Settings /></button>
        </div>
      </div>
      <div hidden={settingsOpen || !showConversations}><OpenConversations codexAvailable={codex?.available} onSetup={openCodex} onDiagnostics={openDiagnostics} /></div>
      {error || codex?.error ? <p className="desktopError" role="alert">{error || codex?.error}</p> : null}
      {settingsOpen ? <div className="desktopSettings" onKeyDown={event => {
        if (event.key === 'Escape' && !event.defaultPrevented) {
          event.preventDefault();
          onSettingsChange(false);
        }
      }}>
        <div className="settingsHeader"><button ref={settingsBack} className="textButton" onClick={() => onSettingsChange(false)}><ArrowLeft aria-hidden="true" /> Back to pad</button><h2>Settings</h2></div>
        <div className="settingsLayout">
        <div className="settingsNavigation" role="tablist" aria-label="Settings sections" onKeyDown={navigateTabs}>
          {settingsPages.map(({id, label, Icon}) => <button key={id} id={`settings-tab-${id}`} type="button" role="tab"
            aria-selected={page === id} aria-controls="settings-panel" tabIndex={page === id ? 0 : -1}
            onClick={() => setPage(id)}><Icon aria-hidden="true" />{label}</button>)}
        </div>
        <div className="desktopSettingsColumns" role="tabpanel" id="settings-panel" aria-labelledby={`settings-tab-${page}`}>
          <section hidden={page !== 'general'}><h3>Appearance</h3>
            <div className="themeOptions" role="group" aria-label="Color theme">
              <button type="button" aria-pressed={lightTheme} onClick={() => onThemeChange(true)}><Sun aria-hidden="true" /> Light</button>
              <button type="button" aria-pressed={!lightTheme} onClick={() => onThemeChange(false)}><Moon aria-hidden="true" /> Dark</button>
            </div>
          </section>
          <section hidden={page !== 'general'}><h3>Sound</h3>
            <label className="desktopCheckbox"><input type="checkbox" checked={audioEnabled} onChange={onAudio} /> Enable sound</label>
          </section>
          <section hidden={page !== 'codex'}><h3>Codex</h3>
            <div className={`codexCheck${codex?.available ? ' ready' : ''}`} role="status">
              {codex?.available ? <CheckCircle2 aria-hidden="true" /> : <CircleAlert aria-hidden="true" />}
              <strong>{checkingCodex || !codex ? 'Checking Codex CLI...' : codex.available ? 'Codex CLI available' : 'Codex CLI not available'}</strong>
            </div>
            <label>Codex executable<div className="desktopInputGroup"><input value={codexPath} placeholder="Automatic detection" onChange={(e) => setCodexPath(e.target.value)} onBlur={() => void savePreferences({codex: codexPath}, true)} />
              <button className="textButton" title="Choose Codex executable" aria-label="Choose Codex executable" onClick={() => void run(async () => {const path = await choosePath(); if (path) {setCodexPath(path); await savePreferences({codex: path}, true);}})}><FolderOpen /></button></div></label>
            {codex?.available && codex.version !== codex.tested_version ? <p className="desktopNotice">Installed Codex {codex.version}. Integration tested with {codex.tested_version}.</p> : null}
            <div className="desktopActions">
              <button className="textButton" disabled={checkingCodex} onClick={() => void checkCodex()}><RefreshCw />{checkingCodex ? 'Checking...' : 'Check again'}</button>
              <button className="textButton" onClick={openDiagnostics}><Stethoscope /> Diagnostics</button>
            </div>
          </section>
          {page === 'devices' ? <div className="deviceSettingsHeading">
            <h3>Devices</h3>
            <div className="deviceTabs" role="tablist" aria-label="Device types" onKeyDown={navigateTabs}>
              {devicePages.map(({id, label, Icon}) => <button key={id} id={`device-tab-${id}`} role="tab"
                aria-selected={devicePage === id} aria-controls="device-panel" tabIndex={devicePage === id ? 0 : -1}
                onClick={() => setDevicePage(id)}><Icon aria-hidden="true" />{label}
                <span className="deviceCount" aria-hidden="true">{id === 'midi' ? Number(Boolean(status?.midi))
                  : paired.devices?.filter(device => device.kind === id && device.connected).length ?? 0}</span>
              </button>)}
            </div>
          </div> : null}
          <div hidden={page !== 'devices'} id="device-panel" role="tabpanel" aria-labelledby={`device-tab-${devicePage}`}>
          <section hidden={devicePage !== 'midi'}>
            {!hardwareTesting ? <div className="deviceIntro"><DeviceIllustration kind="midi" /><div><h3>MIDI controller</h3>
              <p>USB MIDI · Grid and scene controls</p></div></div> : <h3>MIDI controller</h3>}
            <div hidden={hardwareTesting}>
            <label>Profile<select aria-label="Profile" disabled={hardwareTesting} value={profile} onChange={(e) => {setProfile(e.target.value); void savePreferences({midi_profile: e.target.value});}}><option value="">Automatic detection</option>{status?.profiles.map((p) => <option key={p.id} value={p.id}>{p.id}{p.status === 'experimental' ? ' (experimental)' : ''}</option>)}</select></label>
            <label>Input<select aria-label="Input" disabled={hardwareTesting} value={input} onChange={(e) => {setInput(e.target.value); void savePreferences({midi_input: e.target.value});}}><option value="">Automatic detection</option>{input && !status?.inputs.includes(input) ? <option value={input}>{input} (unavailable)</option> : null}{status?.inputs.map((p) => <option key={p}>{p}</option>)}</select></label>
            <label>Output<select aria-label="Output" disabled={hardwareTesting} value={output} onChange={(e) => {setOutput(e.target.value); void savePreferences({midi_output: e.target.value});}}><option value="">Automatic detection</option>{output && !status?.outputs.includes(output) ? <option value={output}>{output} (unavailable)</option> : null}{status?.outputs.map((p) => <option key={p}>{p}</option>)}</select></label>
            <div className="desktopActions"><button className="textButton" title="Refresh devices" aria-label="Refresh devices" disabled={busy || hardwareTesting} onClick={() => void run(refresh)}><RefreshCw /></button>
              <button className="textButton" disabled={busy || hardwareTesting} onClick={() => void run(async () => {await desktopRequest(status?.midi ? 'disconnect_midi' : 'connect_midi', {profile, input, output}); await refresh();})}>{status?.midi ? <Unplug /> : <Plug />}{status?.midi ? 'Disconnect' : 'Connect'}</button></div>
            <p className="desktopNotice">{status?.midi ?? 'No MIDI controller connected'}</p>
            {status?.midi_error ? <p className="desktopError">{status.midi_error}</p> : null}
            </div>
            {page === 'devices' && devicePage === 'midi' ? <HardwareTest profile={profile} input={input} output={output} connected={Boolean(status?.midi)} onActiveChange={setHardwareTesting} /> : null}
          </section>
          <section hidden={devicePage === 'midi'}>
            <div className="deviceIntro"><DeviceIllustration kind={devicePage} /><div>
              <h3>{devicePage === 'stream_deck' ? 'Elgato Stream Deck' : 'Phones, tablets & computers'}</h3>
              <p>{devicePage === 'stream_deck' ? 'Elgato plugin · LCD keys' : 'Virtual Pad · Paired browser'}</p>
              <button className="textButton" onClick={() => onPairDevice(devicePage === 'stream_deck' ? 'stream_deck' : 'browser')}><QrCode aria-hidden="true" /> Pair device</button>
            </div></div>
            {devicePage === 'stream_deck' ? <dl className="deviceSetupFacts">
              <div><dt>Integration</dt><dd>Experimental plugin</dd></div>
              <div><dt>Key configuration</dt><dd>Elgato Stream Deck software</dd></div>
              <div><dt>Starter layouts</dt><dd>15-key, XL, and Neo</dd></div>
              <div><dt>Hardware test</dt><dd>Not yet available</dd></div>
            </dl> : null}
            <div className="desktopActions">
            {devicePage === 'stream_deck' ? <button className="textButton deviceGuide" onClick={() => void run(() => openProjectLink('downloads'))}>
              <Download /> Get plugin</button> : null}
            <button className="textButton deviceGuide" onClick={() => void run(() => openProjectLink(devicePage === 'stream_deck' ? 'stream-deck' : 'connect-browsers'))}>
              <BookOpen /> {devicePage === 'stream_deck' ? 'Plugin setup guide' : 'Browser setup guide'}</button>
            </div>
            {page === 'devices' && devicePage !== 'midi' ? <PairedDevices key={devicePage} state={paired} kind={devicePage} /> : null}
            {devicePage === 'browser' ? <>
              <label className="desktopCheckbox"><input type="checkbox" aria-describedby="browserQuestionSharingHelp" checked={Boolean(status?.settings.share_browser_questions)} disabled={busy}
                onChange={event => {const checked = event.currentTarget.checked;
                  setStatus(previous => previous ? {...previous, settings: {...previous.settings, share_browser_questions: checked}} : previous);
                  void run(async () => {try {await desktopRequest('settings', {share_browser_questions: checked}); await refresh();}
                    catch (reason) {await refresh(); throw reason;}});}} />
                Share Codex questions with paired browsers</label>
              <p className="desktopNotice" id="browserQuestionSharingHelp">Optional, off by default. Paired browsers can still show status, switch chats, and approve, reject, or stop when available. Enable only to read and answer multiple-choice questions there. Question text travels over an unencrypted local connection; use only a trusted network.</p>
            </> : null}
            {status?.network_url ? <div className="networkReady" role="status"><strong>Network access enabled</strong><span>{status.network_url}</span></div>
              : <p className="desktopNotice">Network access is off. Pairing is available on this computer only.</p>}
            <details className="networkSetup" open={!status?.network_url && devicePage !== 'stream_deck'}><summary>{devicePage === 'stream_deck' ? 'Other computer or VM' : 'Network setup'}</summary>
            <label className="desktopCheckbox"><input type="checkbox" checked={sharedNetwork} onChange={e => setSharedNetwork(e.target.checked)} /> VM shared network</label>
            <label>{sharedNetwork ? 'VM IPv4 address' : 'Computer IPv4 address'}<input value={lan} onChange={(e) => setLan(e.target.value)} placeholder={sharedNetwork ? 'e.g. 10.211.55.4' : 'e.g. 192.168.1.45'} /></label>
            {sharedNetwork ? <label>Mac / host IPv4 address<input value={advertiseHost} onChange={e => setAdvertiseHost(e.target.value)} placeholder="e.g. 192.168.1.45" /></label> : null}
            <label>Pairing port<input type="number" min="1" max="65535" value={pairingPort} onChange={e => setPairingPort(e.target.value)} /></label>
            <button className="textButton" disabled={networkBusy} onClick={() => void enableNetwork()}><Wifi />
              {networkBusy ? 'Enabling...' : status?.network_url ? 'Apply network settings' : 'Enable network access'}</button>
            {networkError ? <p className="desktopError" role="alert">{networkError}</p> : null}
            {status?.network_url ? <>
              <button className="textButton" disabled={busy || networkBusy} onClick={() => void run(async () => {await desktopRequest('lan', {host: null}); await refresh();})}><WifiOff aria-hidden="true" />Disable network access</button>
            </> : null}
            </details>
          </section>
          </div>
          {page === 'about' ? <About version={status?.version} /> : null}
        </div>
        </div>
        <button className="textButton" title="Reload the interface without disconnecting conversations"
          onClick={() => window.location.reload()}><RotateCw aria-hidden="true" /> Reload interface</button>
      </div> : null}
    </section>
  );
}
