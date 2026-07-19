import {describe, expect, it} from 'vitest';
import demoManifestData from '../public/experiences/demo-v1.json';
import {createDemoState, demoReducer, demoSurfaceView} from './demo';
import type {DemoManifest} from './types';

const demoManifest = demoManifestData as DemoManifest;

describe('guided demo', () => {
  it('routes the visitor through selection, approval, retry, and success', () => {
    let state = createDemoState(demoManifest);
    state = demoReducer(state, {type: 'select', slot: 1});
    expect(state.stage).toBe('approve_reviewer');
    expect(demoSurfaceView(state).available_actions).toEqual(['approve', 'reject']);

    state = demoReducer(state, {type: 'action', action: 'approve'});
    expect(state.stage).toBe('select_tests');
    state = demoReducer(state, {type: 'select', slot: 2});
    state = demoReducer(state, {type: 'action', action: 'retry'});

    expect(state.stage).toBe('complete');
    expect(demoSurfaceView(state).sessions.every((session) => session.state === 'success')).toBe(true);
  });

  it('does not unlock the sandbox before completion', () => {
    const state = demoReducer(createDemoState(demoManifest), {
      type: 'mode',
      mode: 'sandbox',
    });
    expect(state.mode).toBe('guided');
  });
});
