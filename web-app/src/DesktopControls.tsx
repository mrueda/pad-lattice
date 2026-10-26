import {useCallback, useEffect, useState} from 'react';
import {FolderOpen, Settings, RefreshCw, RotateCw, Plug, Unplug, Wifi, X, Sun, Moon, MonitorSmartphone, SlidersHorizontal, Terminal, Info} from 'lucide-react';
import {choosePath, desktopRequest} from './desktop';
import {OpenConversations} from './OpenConversations';
import {PairedDevices, usePairedDevices} from './PairedDevices';
import {About} from './About';

const settingsPages = [
  {id: 'general', label: 'Appearance & sound', Icon: SlidersHorizontal},
  {id: 'network', label: 'Phones & tablets', Icon: MonitorSmartphone},
  {id: 'midi', label: 'MIDI controller', Icon: Plug},
  {id: 'codex', label: 'Codex', Icon: Terminal},
  {id: 'about', label: 'About', Icon: Info},
] as const;

interface Status {
  version: string;
  settings: {codex?: string; midi_profile?: string; midi_input?: string; midi_output?: string;
    pairing_host?: string; pairing_port?: string; pairing_advertise_host?: string};
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

export function DesktopControls({audioEnabled, onAudio, settingsOpen, onSettingsChange, onPairDevice, lightTheme, onThemeChange}: {
  audioEnabled: boolean;
  onAudio: () => void;
  settingsOpen: boolean;
  onSettingsChange: (open: boolean) => void;
  onPairDevice: () => void;
  lightTheme: boolean;
  onThemeChange: (light: boolean) => void;
}) {
  const [status, setStatus] = useState<Status | null>(null);
  const paired = usePairedDevices();
  const connectedDevices = paired.devices?.filter(device => device.connected).length ?? 0;
  const [page, setPage] = useState<string>('general');
  const [codex, setCodex] = useState<Codex | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
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
      onPairDevice();
    } catch (reason) {
      setNetworkError(String(reason));
    } finally {
      setNetworkBusy(false);
    }
  };
  return (
    <section className="desktopControls">
      <div className="desktopToolbar">
        <div className="desktopConnections">
          <span className="desktopRuntime">{!codex ? 'Checking Codex CLI...' : codex.available ? `Codex CLI ${codex.version}` : 'Codex CLI setup required'}</span>
          <button className={`connectionLink${status?.midi && !status.midi_error ? ' online' : ''}`}
            title={status?.midi_error || status?.midi || 'MIDI controller settings'}
            onClick={() => {setPage('midi'); onSettingsChange(true);}}><Plug aria-hidden="true" />
            MIDI: {!status ? 'checking...' : status.midi_error ? 'unavailable' : status.midi ? 'connected' : 'not connected'}</button>
          <button className={`connectionLink${connectedDevices && !paired.error ? ' online' : ''}`}
            title="View paired devices" onClick={() => {setPage('network'); onSettingsChange(true);}}>
            <MonitorSmartphone aria-hidden="true" />{paired.error ? 'Device status unavailable' : !paired.devices ? 'Checking devices...'
              : `${connectedDevices} ${connectedDevices === 1 ? 'device' : 'devices'} connected`}</button>
          {status?.network_url ? <span title={status.network_url}><Wifi aria-hidden="true" />Network enabled</span> : null}
        </div>
        <div className="desktopActions">
          {!settingsOpen ? <button className="textButton" onClick={() => {setPage('network'); onSettingsChange(true);}}><MonitorSmartphone /> Pair device</button> : null}
          <button className="textButton" title="Settings" aria-label="Settings" aria-expanded={settingsOpen} onClick={() => onSettingsChange(!settingsOpen)}><Settings /></button>
        </div>
      </div>
      <div hidden={settingsOpen}><OpenConversations onSetup={() => {setPage('codex'); onSettingsChange(true);}} /></div>
      {error || codex?.error ? <p className="desktopError" role="alert">{error || codex?.error}</p> : null}
      {codex?.available && !codex.tested ? <p className="desktopNotice">Installed Codex {codex.version}. Integration tested with {codex.tested_version}.</p> : null}
      {settingsOpen ? <div className="desktopSettings">
        <div className="desktopToolbar"><h2>Settings</h2><button className="textButton" title="Close settings" aria-label="Close settings" onClick={() => onSettingsChange(false)}><X /></button></div>
        <div className="settingsLayout">
        <div className="settingsNavigation" role="tablist" aria-label="Settings sections" onKeyDown={event => {
          if (!['ArrowDown', 'ArrowUp', 'ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
          event.preventDefault();
          const tabs = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]'));
          const current = tabs.indexOf(document.activeElement as HTMLButtonElement);
          const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1
            : (current + (['ArrowRight', 'ArrowDown'].includes(event.key) ? 1 : -1) + tabs.length) % tabs.length;
          tabs[next]?.click(); tabs[next]?.focus();
        }}>
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
            <label>Codex executable<div className="desktopInputGroup"><input value={codexPath} placeholder="Automatic detection" onChange={(e) => setCodexPath(e.target.value)} onBlur={() => void savePreferences({codex: codexPath}, true)} />
              <button className="textButton" title="Choose Codex executable" aria-label="Choose Codex executable" onClick={() => void run(async () => {const path = await choosePath(); if (path) {setCodexPath(path); await savePreferences({codex: path}, true);}})}><FolderOpen /></button></div></label>
          </section>
          <section hidden={page !== 'midi'}><h3>MIDI controller</h3>
            <label>Profile<select value={profile} onChange={(e) => {setProfile(e.target.value); void savePreferences({midi_profile: e.target.value});}}><option value="">Automatic detection</option>{status?.profiles.map((p) => <option key={p.id} value={p.id}>{p.id}{p.status === 'experimental' ? ' (experimental)' : ''}</option>)}</select></label>
            <label>Input<select value={input} onChange={(e) => {setInput(e.target.value); void savePreferences({midi_input: e.target.value});}}><option value="">Automatic detection</option>{input && !status?.inputs.includes(input) ? <option value={input}>{input} (unavailable)</option> : null}{status?.inputs.map((p) => <option key={p}>{p}</option>)}</select></label>
            <label>Output<select value={output} onChange={(e) => {setOutput(e.target.value); void savePreferences({midi_output: e.target.value});}}><option value="">Automatic detection</option>{output && !status?.outputs.includes(output) ? <option value={output}>{output} (unavailable)</option> : null}{status?.outputs.map((p) => <option key={p}>{p}</option>)}</select></label>
            <div className="desktopActions"><button className="textButton" title="Refresh devices" aria-label="Refresh devices" disabled={busy} onClick={() => void run(refresh)}><RefreshCw /></button>
              <button className="textButton" disabled={busy} onClick={() => void run(async () => {await desktopRequest(status?.midi ? 'disconnect_midi' : 'connect_midi', {profile, input, output}); await refresh();})}>{status?.midi ? <Unplug /> : <Plug />}{status?.midi ? 'Disconnect' : 'Connect'}</button></div>
            <p className="desktopNotice">{status?.midi ?? 'No MIDI controller connected'}</p>
            {status?.midi_error ? <p className="desktopError">{status.midi_error}</p> : null}
          </section>
          <section hidden={page !== 'network'}>
            <div className="desktopToolbar"><h3>Phones & tablets</h3>
              <button className="textButton" onClick={onPairDevice}><MonitorSmartphone /> Pair device</button></div>
            {page === 'network' ? <PairedDevices state={paired} /> : null}
            {status?.network_url ? <div className="networkReady" role="status"><strong>Network access enabled</strong><span>{status.network_url}</span></div>
              : <p className="desktopNotice">Network access is off. Pairing is available on this computer only.</p>}
            <details className="networkSetup" open={!status?.network_url}><summary>Network setup</summary>
            <label className="desktopCheckbox"><input type="checkbox" checked={sharedNetwork} onChange={e => setSharedNetwork(e.target.checked)} /> VM shared network</label>
            <label>{sharedNetwork ? 'VM IPv4 address' : 'Computer IPv4 address'}<input value={lan} onChange={(e) => setLan(e.target.value)} placeholder={sharedNetwork ? 'e.g. 10.211.55.4' : 'e.g. 192.168.1.45'} /></label>
            {sharedNetwork ? <label>Mac / host IPv4 address<input value={advertiseHost} onChange={e => setAdvertiseHost(e.target.value)} placeholder="e.g. 192.168.1.45" /></label> : null}
            <label>Pairing port<input type="number" min="1" max="65535" value={pairingPort} onChange={e => setPairingPort(e.target.value)} /></label>
            <button className="textButton" disabled={networkBusy} onClick={() => void enableNetwork()}><Wifi />
              {networkBusy ? 'Enabling...' : status?.network_url ? 'Apply network settings' : 'Enable network access'}</button>
            {networkError ? <p className="desktopError" role="alert">{networkError}</p> : null}
            {status?.network_url ? <>
              <button className="textButton" disabled={busy || networkBusy} onClick={() => void run(async () => {await desktopRequest('lan', {host: null}); await refresh();})}>Disable network access</button>
            </> : null}
            </details>
          </section>
          {page === 'about' ? <About version={status?.version} /> : null}
        </div>
        </div>
        <button className="textButton" title="Reload the interface without disconnecting conversations"
          onClick={() => window.location.reload()}><RotateCw aria-hidden="true" /> Reload interface</button>
      </div> : null}
    </section>
  );
}
