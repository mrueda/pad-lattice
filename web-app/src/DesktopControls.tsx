import {useCallback, useEffect, useState} from 'react';
import {FolderOpen, Settings, RefreshCw, RotateCw, Plug, Unplug, Wifi, X} from 'lucide-react';
import {choosePath, desktopRequest} from './desktop';
import {OpenConversations} from './OpenConversations';

interface Status {
  version: string;
  settings: {codex?: string; midi_profile?: string; midi_input?: string; midi_output?: string};
  inputs: string[];
  outputs: string[];
  profiles: Array<{id: string; status: string}>;
  midi: string | null;
  midi_error: string | null;
  lan_host: string;
  port: number;
}
interface Codex {available: boolean; version?: string; tested?: boolean; tested_version: string; error?: string}

export function DesktopControls() {
  const [status, setStatus] = useState<Status | null>(null);
  const [codex, setCodex] = useState<Codex | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [codexPath, setCodexPath] = useState('');
  const [profile, setProfile] = useState('');
  const [input, setInput] = useState('');
  const [output, setOutput] = useState('');
  const [lan, setLan] = useState('');
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
      if (next.lan_host !== '127.0.0.1') setLan(next.lan_host);
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
  return (
    <section className="desktopControls">
      <div className="desktopToolbar">
        <div className="desktopConnections">
          <span className="desktopRuntime">{codex?.available ? `Codex CLI ${codex.version}` : 'Codex CLI setup required'}</span>
          <span><Plug aria-hidden="true" />MIDI: {status?.midi ? 'connected' : 'not connected'}</span>
          <span><Wifi aria-hidden="true" />Phone pairing: {status && status.lan_host !== '127.0.0.1' ? 'enabled' : 'off'}</span>
        </div>
        <button className="textButton" title="Settings" aria-label="Settings" onClick={() => setSettingsOpen(!settingsOpen)}><Settings /></button>
      </div>
      <OpenConversations />
      {error || codex?.error ? <p className="desktopError" role="alert">{error || codex?.error}</p> : null}
      {codex?.available && !codex.tested ? <p className="desktopNotice">Installed Codex {codex.version}. Integration tested with {codex.tested_version}.</p> : null}
      {settingsOpen ? <div className="desktopSettings">
        <div className="desktopToolbar"><h2>Settings</h2><button className="textButton" title="Close settings" aria-label="Close settings" onClick={() => setSettingsOpen(false)}><X /></button></div>
        <div className="desktopSettingsColumns">
          <section><h3>Codex</h3>
            <label>Codex executable<div className="desktopInputGroup"><input value={codexPath} placeholder="Automatic detection" onChange={(e) => setCodexPath(e.target.value)} onBlur={() => void savePreferences({codex: codexPath}, true)} />
              <button className="textButton" title="Choose Codex executable" aria-label="Choose Codex executable" onClick={() => void run(async () => {const path = await choosePath(); if (path) {setCodexPath(path); await savePreferences({codex: path}, true);}})}><FolderOpen /></button></div></label>
          </section>
          <section><h3>MIDI controller</h3>
            <label>Profile<select value={profile} onChange={(e) => {setProfile(e.target.value); void savePreferences({midi_profile: e.target.value});}}><option value="">Automatic detection</option>{status?.profiles.map((p) => <option key={p.id} value={p.id}>{p.id}{p.status === 'experimental' ? ' (experimental)' : ''}</option>)}</select></label>
            <label>Input<select value={input} onChange={(e) => {setInput(e.target.value); void savePreferences({midi_input: e.target.value});}}><option value="">Automatic detection</option>{input && !status?.inputs.includes(input) ? <option value={input}>{input} (unavailable)</option> : null}{status?.inputs.map((p) => <option key={p}>{p}</option>)}</select></label>
            <label>Output<select value={output} onChange={(e) => {setOutput(e.target.value); void savePreferences({midi_output: e.target.value});}}><option value="">Automatic detection</option>{output && !status?.outputs.includes(output) ? <option value={output}>{output} (unavailable)</option> : null}{status?.outputs.map((p) => <option key={p}>{p}</option>)}</select></label>
            <div className="desktopActions"><button className="textButton" title="Refresh devices" aria-label="Refresh devices" disabled={busy} onClick={() => void run(refresh)}><RefreshCw /></button>
              <button className="textButton" disabled={busy} onClick={() => void run(async () => {await desktopRequest(status?.midi ? 'disconnect_midi' : 'connect_midi', {profile, input, output}); await refresh();})}>{status?.midi ? <Unplug /> : <Plug />}{status?.midi ? 'Disconnect' : 'Connect'}</button></div>
            <p className="desktopNotice">{status?.midi ?? 'No MIDI controller connected'}</p>
            {status?.midi_error ? <p className="desktopError">{status.midi_error}</p> : null}
          </section>
          <section><h3>Phone and tablet</h3>
            <label>Private IPv4 address<input value={lan} onChange={(e) => setLan(e.target.value)} placeholder="192.168.1.45" /></label>
            <button className="textButton" disabled={busy || !lan} onClick={() => void run(async () => {await desktopRequest('lan', {host: lan}); await refresh();})}><Wifi /> Enable pairing</button>
            {status?.lan_host !== '127.0.0.1' && status ? <><p className="desktopNotice">{`http://${status.lan_host}:${status.port}`}</p><button className="textButton" disabled={busy} onClick={() => void run(async () => {await desktopRequest('lan', {host: null}); await refresh();})}>Disable pairing</button></> : null}
          </section>
        </div>
        <button className="textButton" title="Reload the interface without disconnecting conversations"
          onClick={() => window.location.reload()}><RotateCw aria-hidden="true" /> Reload interface</button>
      </div> : null}
    </section>
  );
}
