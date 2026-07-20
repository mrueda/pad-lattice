import {describe, expect, it} from 'vitest';
import demoManifestData from '../public/experiences/demo-v1.json';
import {createDemoState, demoGuidance, demoReducer, demoSurfaceView} from './demo';
import type {DemoManifest} from './types';

const demoManifest = demoManifestData as DemoManifest;

describe('guided demo', () => {
  it('routes the visitor through selection, approval, retry, and success', () => {
    let state = createDemoState(demoManifest);
    expect(demoGuidance(state)).toMatchObject({
      title: 'Select Reviewer - Scene 2',
      slot: 1,
      action: null,
    });
    state = demoReducer(state, {type: 'select', slot: 1});
    expect(state.stage).toBe('approve_reviewer');
    expect(demoSurfaceView(state).available_actions).toEqual(['approve', 'reject']);
    expect(demoGuidance(state)).toMatchObject({
      title: 'Approve Reviewer',
      slot: null,
      action: 'approve',
    });

    state = demoReducer(state, {type: 'action', action: 'approve'});
    expect(state.stage).toBe('select_tests');
    state = demoReducer(state, {type: 'select', slot: 2});
    state = demoReducer(state, {type: 'action', action: 'retry'});

    expect(state.stage).toBe('complete');
    expect(demoSurfaceView(state).sessions.every((session) => session.state === 'success')).toBe(true);
    expect(demoGuidance(state)).toBeNull();
  });

  it('opens the sandbox immediately and applies its state actions', () => {
    let state = demoReducer(createDemoState(demoManifest), {
      type: 'mode',
      mode: 'sandbox',
    });
    expect(state.mode).toBe('sandbox');
    expect(state.sessions).toHaveLength(8);

    state = demoReducer(state, {
      type: 'set_state',
      slot: 0,
      state: 'waiting_for_approval',
    });
    expect(demoSurfaceView(state).available_actions).toEqual(['approve', 'reject']);

    state = demoReducer(state, {type: 'action', action: 'approve'});
    expect(state.sessions[0].state).toBe('success');
  });
});
