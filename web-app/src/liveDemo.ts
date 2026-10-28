import {useEffect, useState} from 'react';
import {parseDemoManifest} from './experiences';
import type {DemoManifest, ExperienceStateMessage, SurfaceView} from './types';

export function demoGuide(manifest: DemoManifest | null, experience: ExperienceStateMessage | null, view: SurfaceView) {
  if (!manifest || experience?.kind !== 'demo' || experience.status !== 'playing'
      || experience.cue_index == null || !Number.isInteger(experience.cue_index)) return null;
  const stage = manifest.stages[experience.cue_index];
  if (!stage || stage.view.sessions.length !== view.sessions.length
      || !stage.view.sessions.every(expected => view.sessions.some(actual => actual.slot === expected.slot
        && actual.state === expected.state && actual.label === expected.label))) return null;
  const target = stage.guide_target;
  if (!target) return null;
  if (target.event === 'select') {
    const session = view.sessions.find(item => item.slot === target.slot);
    return session ? {...target, label: `Select ${session.label}`, detail: `Scene ${session.slot + 1} on the right`} : null;
  }
  const selected = view.sessions.find(item => item.selected);
  const expected = stage.view.sessions.find(item => item.selected);
  if (!selected || selected.slot !== expected?.slot || !target.action || !view.available_actions.includes(target.action)) return null;
  const label = {approve: 'Approve', reject: 'Reject', stop: 'Stop', retry: 'Retry'}[target.action];
  return {...target, label: `${label} ${selected.label}`, detail: `${label} control above the grid`};
}

export function useLiveDemo(active: boolean, experience: ExperienceStateMessage | null, view: SurfaceView) {
  const [manifest, setManifest] = useState<DemoManifest | null>(null);
  useEffect(() => {
    if (!active || manifest) return;
    const controller = new AbortController();
    fetch('./experiences/demo-v1.json', {signal: controller.signal})
      .then(response => {if (!response.ok) throw Error('Demo unavailable'); return response.json();})
      .then(data => {if (!controller.signal.aborted) setManifest(parseDemoManifest(data));})
      .catch(() => {}); // Server captions remain available if local guidance cannot load.
    return () => controller.abort();
  }, [active, manifest]);
  return active ? demoGuide(manifest, experience, view) : null;
}
