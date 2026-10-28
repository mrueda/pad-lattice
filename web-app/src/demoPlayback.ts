import {useEffect, useMemo, useState} from 'react';
import {createDemoState, demoTarget, demoReducer, type DemoState} from './demo';
import type {DemoManifest} from './types';

export const DEMO_STEP_MS = 7000;

export function demoPlaybackSteps(manifest: DemoManifest): DemoState[] {
  const steps: DemoState[] = [];
  const visited = new Set<string>();
  let state = createDemoState(manifest);
  while (!visited.has(state.stage)) {
    visited.add(state.stage);
    steps.push(state);
    const stage = manifest.stages.find((item) => item.id === state.stage)!;
    if (stage.terminal) return steps;
    const target = stage.guide_target;
    if (!target) break;
    state = target.event === 'select' && target.slot !== null
      ? demoReducer(state, {type: 'select', slot: target.slot})
      : target.action !== null ? demoReducer(state, {type: 'action', action: target.action}) : state;
  }
  throw new Error('The Demo needs a finite guided path to a terminal stage.');
}

export function demoPlaybackFrame(steps: DemoState[], elapsed: number) {
  const index = Math.min(Math.floor(Math.max(0, elapsed) / DEMO_STEP_MS), steps.length - 1);
  const state = steps[index];
  const target = demoTarget(state);
  const local = Math.max(0, elapsed) - index * DEMO_STEP_MS;
  return {
    state, target,
    pointer: target && local >= 4200 ? {pressed: local >= 6650, approach: Math.min(1, (local - 4200) / 700)} : null,
  };
}

export function useDemoPlayback(manifest: DemoManifest, active: boolean) {
  const steps = useMemo(() => demoPlaybackSteps(manifest), [manifest]);
  const duration = steps.length * DEMO_STEP_MS;
  const [elapsed, setElapsed] = useState(0);
  const [paused, setPaused] = useState(false);
  const [run, setRun] = useState(0);
  const [visible, setVisible] = useState(() => !document.hidden);
  const finished = elapsed >= duration;
  useEffect(() => {
    const update = () => setVisible(!document.hidden);
    document.addEventListener('visibilitychange', update);
    return () => document.removeEventListener('visibilitychange', update);
  }, []);
  useEffect(() => {
    if (!active || paused || finished || !visible) return;
    let previous = performance.now();
    const timer = window.setInterval(() => {
      const now = performance.now();
      // Long stalls must not skip the explanation or the demonstrated click.
      const delta = Math.min(250, Math.max(0, now - previous));
      previous = now;
      setElapsed((value) => Math.min(duration, value + delta));
    }, 50);
    return () => window.clearInterval(timer);
  }, [active, duration, finished, paused, visible]);
  const frame = demoPlaybackFrame(steps, elapsed);
  return {
    ...frame, elapsed, duration, paused, finished,
    state: {...frame.state, audioSequence: run * steps.length + frame.state.audioSequence},
    toggle: () => setPaused((value) => !value),
    replay: () => {setElapsed(0); setPaused(false); setRun((value) => value + 1);},
  };
}
