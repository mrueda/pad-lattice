import {useEffect, useRef, useState} from 'react';
import {Check, Download, FlaskConical, Square, X, SkipForward} from 'lucide-react';
import {desktopRequest, saveProfileReport} from './desktop';
import {VirtualSurface} from './VirtualSurface';
import type {ControlAction, SurfaceMessage} from './types';

interface TestSnapshot {
  run_id: string;
  status: 'running' | 'completed' | 'cancelled';
  index: number;
  total: number;
  failure_stage: string | null;
  step: {id: string; group: string; key: string; prompt: string; seconds_left: number | null} | null;
  last_result: {prompt: string; passed: boolean} | null;
  surface: SurfaceMessage | null;
  results: Record<string, Record<string, boolean>>;
}

const reasons: Record<string, string> = {
  cancelled: 'Test stopped.', live_session: 'Test stopped: a Codex conversation connected.',
  playback: 'Test stopped: playback started.', interface_timeout: 'Test stopped: the interface disconnected.',
  shutdown: 'Test stopped: Desktop closed.', initialize: 'Could not open the controller.',
  input: 'The controller stopped responding.', output: 'Could not update the controller lights.',
  close: 'The controller could not be closed cleanly.',
  disconnected: 'Test stopped: the controller disconnected.',
};

export function HardwareTest({profile, input, output, connected, onActiveChange}: {
  profile: string; input: string; output: string; connected: boolean; onActiveChange: (active: boolean) => void;
}) {
  const [test, setTest] = useState<TestSnapshot | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const current = useRef<TestSnapshot | null>(null);
  const mounted = useRef(false);
  const pending = useRef(false);
  const sequence = useRef(0);
  const accept = (value: TestSnapshot | null) => { current.current = value; setTest(value); };

  useEffect(() => { setConfirmed(false); }, [profile, input, output]);
  useEffect(() => {
    mounted.current = true;
    let disposed = false;
    let polling = false;
    const poll = async () => {
      if (pending.current || polling) return;
      polling = true;
      const id = ++sequence.current;
      try {
        const value = await desktopRequest<TestSnapshot | null>('profile_test_status');
        if (!disposed && id === sequence.current) accept(value);
      } catch (reason) {
        if (!disposed) setError(String(reason));
      } finally { polling = false; }
    };
    void poll();
    const timer = window.setInterval(() => void poll(), 500);
    return () => {
      disposed = true; mounted.current = false; clearInterval(timer);
      if (current.current?.status === 'running') {
        void desktopRequest('profile_test_cancel', {run_id: current.current.run_id}).catch(() => {});
      }
    };
  }, []);

  const command = async (method: string, params: object = {}) => {
    pending.current = true; ++sequence.current; setBusy(true); setError(''); setSaved(false);
    try {
      const next = await desktopRequest<TestSnapshot>(method, params);
      if (mounted.current) accept(next);
      else if (next.status === 'running') {
        await desktopRequest('profile_test_cancel', {run_id: next.run_id});
      }
    } catch (reason) { if (mounted.current) setError(String(reason)); }
    finally { pending.current = false; if (mounted.current) setBusy(false); }
  };
  const answer = (passed: boolean) => command('profile_test_answer', {
    run_id: test?.run_id, step_id: test?.step?.id, passed,
  });
  const active = test?.status === 'running';
  useEffect(() => { onActiveChange(active); return () => onActiveChange(false); }, [active, onActiveChange]);
  const passed = test?.status === 'completed' && !test.failure_stage &&
    Object.values(test.results).every(group => Object.values(group).every(Boolean));
  const ready = Boolean(profile && input && output && !connected);

  return <div className="hardwareTest">
    <h3>Hardware test</h3>
    {!active ? <>
      <label className="desktopCheckbox"><input type="checkbox" checked={confirmed} disabled={!ready || busy}
        onChange={event => setConfirmed(event.target.checked)} /> These ports belong to my controller</label>
      <button className="textButton" disabled={!ready || !confirmed || busy}
        onClick={() => void command('profile_test_start', {profile, input, output, confirmed})}>
        <FlaskConical /> {test ? 'Run again' : 'Start hardware test'}</button>
      {!ready ? <p className="desktopNotice">{connected ? 'Disconnect MIDI before testing.' : 'Select a profile and both MIDI ports.'}</p> : null}
    </> : <>
      <div className="hardwareTestHeading"><span>Step {test.index} of {test.total}</span>
        <button className="textButton" disabled={busy} onClick={() => void command('profile_test_cancel', {run_id: test.run_id})}><Square /> Stop test</button></div>
      <progress value={test.index - 1} max={test.total} aria-label="Hardware test progress" />
      <div className="hardwareTestBody">
        {test.surface ? <div className="hardwareTestPreview" aria-label="Expected controller lights">
          <VirtualSurface frame={test.surface.visual_frame} view={test.surface.view} disabled
            guidedAction={test.step?.group === 'actions' ? test.step.key as ControlAction : null}
            guidedSlot={test.step?.group === 'selectors' ? Number(test.step.key) - 1 : null}
            onAction={() => {}} onSelect={() => {}} />
        </div> : null}
        <div className="hardwareTestStep" aria-live="polite">
          <h4>{test.step?.prompt}</h4>
          {test.step?.group === 'visual' ? <div className="desktopActions">
            <button className="textButton" disabled={busy} onClick={() => void answer(true)}><Check /> Matches</button>
            <button className="textButton" disabled={busy} onClick={() => void answer(false)}><X /> Does not match</button>
          </div> : <>
            <p>Waiting for controller: {test.step?.seconds_left}s</p>
            <button className="textButton" disabled={busy} onClick={() => void answer(false)}><SkipForward /> Skip check</button>
          </>}
          {test.last_result ? <p className="desktopNotice">{test.last_result.passed ? 'Passed' : 'Not confirmed'}: {test.last_result.prompt}</p> : null}
        </div>
      </div>
    </>}
    {test && !active ? <div className="hardwareTestResult" role="status">
      <strong>{test.failure_stage ? reasons[test.failure_stage] ?? 'Test stopped.' : passed ? 'All checks passed' : 'Completed with unconfirmed checks'}</strong>
      <span>{Object.values(test.results).flatMap(Object.values).filter(Boolean).length} of {test.total} checks passed</span>
      <button className="textButton" disabled={busy} onClick={async () => {
        setBusy(true); setError('');
        try { setSaved(await saveProfileReport(test.run_id)); } catch (reason) { setError(String(reason)); }
        finally { setBusy(false); }
      }}><Download /> Export report</button>
      {saved ? <span>Report saved</span> : null}
    </div> : null}
    {error ? <p className="desktopError" role="alert">{error}</p> : null}
  </div>;
}
