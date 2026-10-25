import {useCallback, useEffect, useState} from 'react';
import {FolderOpen, Play, Settings, RefreshCw, Plug, Unplug, Wifi, Save, X} from 'lucide-react';
import {choosePath, desktopRequest} from './desktop';

interface Status {
  version: string;
  settings: {codex?: string; terminal?: string};
  terminals: string[];
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
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [cwd, setCwd] = useState('');
  const [label, setLabel] = useState('');
  const [resume, setResume] = useState('');
  const [codexPath, setCodexPath] = useState('');
  const [terminal, setTerminal] = useState('');
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
      setTerminal(next.settings.terminal ?? '');
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
    setBusy(true); setError(''); setNotice('');
    try { await work(); } catch (reason) { setError(String(reason)); } finally { setBusy(false); }
  };
  return (
    <section className="desktopControls">
      <div className="desktopToolbar">
        <span className="desktopRuntime">{codex?.available ? `Codex ${codex.version}` : 'Codex setup required'}</span>
        <button className="textButton" title="Settings" aria-label="Settings" onClick={() => setSettingsOpen(!settingsOpen)}><Settings /></button>
      </div>
      <form className="desktopSession" onSubmit={(event) => {
        event.preventDefault();
        void run(async () => {
          await desktopRequest('launch_session', {cwd, label, resume});
          setNotice('Terminal opened. Review Pad-Lattice hooks with /hooks when Codex asks.');
        });
      }}>
        <label className="projectField">Project folder
          <div className="desktopInputGroup"><input value={cwd} onChange={(e) => setCwd(e.target.value)} placeholder="Choose a project" required />
            <button type="button" className="textButton" title="Choose project folder" aria-label="Choose project folder" onClick={() => void run(async () => {
              const path = await choosePath(true); if (path) { setCwd(path); if (!label) setLabel(path.split('/').filter(Boolean).pop() ?? 'work'); }
            })}><FolderOpen /></button></div>
        </label>
        <label>Session label<input value={label} onChange={(e) => setLabel(e.target.value)} maxLength={64} placeholder="implementation" required /></label>
        <label>Resume ID <span className="muted">(optional)</span><input value={resume} onChange={(e) => setResume(e.target.value)} placeholder="New session" /></label>
        <button className="primaryButton" type="submit" disabled={busy || !codex?.available}><Play />{resume ? 'Resume session' : 'Start session'}</button>
      </form>
      {error || codex?.error ? <p className="desktopError" role="alert">{error || codex?.error}</p> : null}
      {notice ? <p className="desktopNotice" role="status">{notice}</p> : null}
      {codex?.available && !codex.tested ? <p className="desktopNotice">Installed Codex {codex.version}. Integration tested with {codex.tested_version}.</p> : null}
      {settingsOpen ? <div className="desktopSettings">
        <div className="desktopToolbar"><h2>Settings</h2><button className="textButton" title="Close settings" aria-label="Close settings" onClick={() => setSettingsOpen(false)}><X /></button></div>
        <div className="desktopSettingsColumns">
          <section><h3>Codex and terminal</h3>
            <label>Codex executable<div className="desktopInputGroup"><input value={codexPath} placeholder="Automatic detection" onChange={(e) => setCodexPath(e.target.value)} />
              <button className="textButton" title="Choose Codex executable" aria-label="Choose Codex executable" onClick={() => void run(async () => {const path = await choosePath(false); if (path) setCodexPath(path);})}><FolderOpen /></button></div></label>
            <label>Terminal<select value={terminal} onChange={(e) => setTerminal(e.target.value)}><option value="">Automatic detection</option>{status?.terminals.map((name) => <option key={name}>{name}</option>)}</select></label>
            <button className="textButton" disabled={busy} onClick={() => void run(async () => {
              await desktopRequest('settings', {codex: codexPath, terminal});
              setCodex(await desktopRequest<Codex>('inspect_codex')); await refresh(); setNotice('Settings saved.');
            })}><Save /> Save</button>
          </section>
          <section><h3>MIDI controller</h3>
            <label>Profile<select value={profile} onChange={(e) => setProfile(e.target.value)}><option value="">Automatic detection</option>{status?.profiles.map((p) => <option key={p.id} value={p.id}>{p.id}{p.status === 'experimental' ? ' (experimental)' : ''}</option>)}</select></label>
            <label>Input<select value={input} onChange={(e) => setInput(e.target.value)}><option value="">Automatic detection</option>{status?.inputs.map((p) => <option key={p}>{p}</option>)}</select></label>
            <label>Output<select value={output} onChange={(e) => setOutput(e.target.value)}><option value="">Automatic detection</option>{status?.outputs.map((p) => <option key={p}>{p}</option>)}</select></label>
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
      </div> : null}
    </section>
  );
}
