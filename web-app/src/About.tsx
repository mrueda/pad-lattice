import {useState} from 'react';
import {BookOpen, Github, Copy, Check, Scale} from 'lucide-react';
import {desktopRequest, openProjectLink} from './desktop';
import {diagnosticsReport} from './diagnostics';
import license from '../../LICENSE?raw';

const credits = [
  ['React / React DOM', 'Interface', 'MIT'],
  ['Lucide', 'Icons', 'ISC'],
  ['Tauri / Tauri API', 'Desktop runtime', 'MIT OR Apache-2.0'],
  ['Tauri dialog / single-instance plugins', 'Native integration', 'MIT OR Apache-2.0'],
  ['serde_json', 'Native JSON messages', 'MIT OR Apache-2.0'],
  ['Python', 'Local engine', 'PSF-2.0'],
  ['Mido', 'MIDI messages', 'MIT'],
  ['python-rtmidi / RtMidi', 'MIDI device access', 'MIT / modified MIT'],
  ['Segno', 'Pairing QR codes', 'BSD-3-Clause'],
  ['websockets', 'Browser connections', 'BSD-3-Clause'],
];

export function About({version}: {version?: string}) {
  const [error, setError] = useState('');
  const [report, setReport] = useState('');
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notices, setNotices] = useState('');
  const [loadingNotices, setLoadingNotices] = useState(false);
  const loadNotices = async () => {
    setLoadingNotices(true); setError('');
    try {
      const response = await fetch('./third-party-notices.txt');
      if (!response.ok) throw new Error('Could not load third-party notices.');
      const text = await response.text();
      if (!text.startsWith('PAD-LATTICE THIRD-PARTY NOTICES')) throw new Error('Third-party notices are unavailable.');
      setNotices(text);
    } catch (reason) {setError(String(reason));}
    finally {setLoadingNotices(false);}
  };
  const copyDiagnostics = async () => {
    setBusy(true); setCopied(false); setError('');
    const results = await Promise.all(['status', 'inspect_codex', 'paired_devices'].map(method =>
      desktopRequest(method).catch(() => null)));
    const text = diagnosticsReport(...results as [unknown, unknown, unknown]);
    setReport(text);
    try {await navigator.clipboard.writeText(text); setCopied(true);}
    catch {setError('Clipboard unavailable. Diagnostics are shown below.');}
    finally {setBusy(false);}
  };
  const open = async (destination: 'docs' | 'github') => {
    try {await openProjectLink(destination); setError('');}
    catch (reason) {setError(String(reason));}
  };
  return <section className="desktopAbout" aria-label="About Pad-Lattice">
    <h3>Pad-Lattice</h3>
    <p className="desktopNotice">{version ? `Version ${version}` : 'Version unavailable'} · Apache-2.0</p>
    <p className="desktopNotice">Copyright (C) 2026 Manuel Rueda.</p>
    <div className="desktopActions">
      <button className="textButton" onClick={() => void open('docs')}><BookOpen /> Documentation</button>
      <button className="textButton" onClick={() => void open('github')}><Github /> GitHub</button>
      <button className="textButton" disabled={busy} onClick={() => void copyDiagnostics()}>{copied ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}{busy ? 'Collecting...' : 'Copy diagnostics'}</button>
    </div>
    {copied ? <p className="desktopNotice" role="status">Diagnostics copied</p> : null}
    {error ? <p className="desktopError" role="alert">{error}</p> : null}
    {report ? <details open={!copied}><summary>Diagnostics</summary><pre tabIndex={0}>{report}</pre></details> : null}
    <details><summary>Pad-Lattice license</summary><pre>{license}</pre></details>
    <h3>Third-party credits</h3>
    <p className="desktopNotice">Core runtime libraries. Each retains its own license.</p>
    <button className="textButton" disabled={loadingNotices} onClick={() => void loadNotices()}><Scale aria-hidden="true" />{loadingNotices ? 'Loading...' : 'Bundled dependency notices'}</button>
    {notices ? <details open><summary>Dependency notices</summary><pre tabIndex={0}>{notices}</pre></details> : null}
    <ul className="thirdPartyCredits">{credits.map(([name, purpose, terms]) => <li key={name}>
      <div><strong>{name}</strong><small>{purpose}</small></div><span>{terms}</span>
    </li>)}</ul>
  </section>;
}
