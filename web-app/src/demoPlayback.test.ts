import {describe, expect, it} from 'vitest';
import data from '../public/experiences/demo-v1.json';
import {DEMO_STEP_MS, demoPlaybackFrame, demoPlaybackSteps} from './demoPlayback';
import type {DemoManifest} from './types';

const manifest = data as DemoManifest;
describe('autoplay Demo', () => {
  it('compiles the shared graph into a 35-second approve/reject walkthrough', () => {
    const steps = demoPlaybackSteps(manifest);
    expect(steps.map((step) => step.stage)).toEqual(['select_reviewer', 'approve_reviewer', 'select_tests', 'reject_tests', 'complete']);
    expect(steps.length * DEMO_STEP_MS).toBe(35000);
    expect(demoPlaybackFrame(steps, 14000).state.manifest).toBe(manifest);
    expect(demoPlaybackFrame(steps, 35000).target).toBeNull();
  });
  it('shows the pointer before the click and keeps outcomes deterministic', () => {
    const steps = demoPlaybackSteps(manifest);
    expect(demoPlaybackFrame(steps, 0).pointer).toBeNull();
    expect(demoPlaybackFrame(steps, 6000)).toMatchObject({target: {slot: 1}, pointer: {pressed: false, approach: 1}});
    expect(demoPlaybackFrame(steps, 6800).pointer?.pressed).toBe(true);
    expect(demoPlaybackFrame(steps, 7000).state.stage).toBe('approve_reviewer');
    expect(demoPlaybackFrame(steps, 21000).state.stage).toBe('reject_tests');
    expect(demoPlaybackFrame(steps, 1e6).state.stage).toBe('complete');
    expect(demoPlaybackFrame(steps, -1).state.stage).toBe('select_reviewer');
  });
  it('rejects a cyclic or missing guided path rather than playing forever', () => {
    const invalid = structuredClone(manifest);
    invalid.stages[0].transitions[0].next_stage = invalid.initial_stage;
    expect(() => demoPlaybackSteps(invalid)).toThrow('finite guided path');
    invalid.stages[0].guide_target = null;
    expect(() => demoPlaybackSteps(invalid)).toThrow('finite guided path');
  });
});
