import {describe, expect, it} from 'vitest';
import demoManifestData from '../public/experiences/demo-v1.json';
import {createDemoState, demoTarget, demoReducer, demoSurfaceView} from './demo';
import type {DemoManifest} from './types';

const demoManifest = demoManifestData as DemoManifest;

describe('guided demo', () => {
  it('routes selection, approval, and rejection to the intended agents', () => {
    let state = createDemoState(demoManifest);
    expect(demoTarget(state)).toMatchObject({
      slot: 1,
      action: null,
    });
    state = demoReducer(state, {type: 'select', slot: 1});
    expect(state.stage).toBe('approve_reviewer');
    expect(demoSurfaceView(state).available_actions).toEqual(['approve', 'reject']);
    expect(demoTarget(state)).toMatchObject({
      slot: null,
      action: 'approve',
    });

    state = demoReducer(state, {type: 'action', action: 'approve'});
    expect(state.stage).toBe('select_tests');
    expect(demoSurfaceView(state).sessions[1].state).toBe('running');
    state = demoReducer(state, {type: 'select', slot: 2});
    state = demoReducer(state, {type: 'action', action: 'reject'});

    expect(state.stage).toBe('complete');
    expect(demoSurfaceView(state).sessions.map((session) => session.state)).toEqual(['running', 'success', 'cancelled']);
    expect(demoTarget(state)).toBeNull();
  });

  it('ignores unrelated controls and can end after declining the first request', () => {
    let state = createDemoState(demoManifest);
    expect(demoReducer(state, {type: 'action', action: 'approve'})).toBe(state);
    expect(demoReducer(state, {type: 'select', slot: 7})).toBe(state);
    state = demoReducer(state, {type: 'select', slot: 1});
    state = demoReducer(state, {type: 'action', action: 'reject'});
    expect(state.stage).toBe('review_declined');
    expect(demoSurfaceView(state).available_actions).toEqual([]);
    const reset = demoReducer(state, {type: 'reset'});
    expect(reset.stage).toBe(demoManifest.initial_stage);
    expect(reset.audioSequence).toBeGreaterThan(state.audioSequence);
  });
});
