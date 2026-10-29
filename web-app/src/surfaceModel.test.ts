import {describe, expect, it} from 'vitest';
import {compileVisualFrame} from './surfaceModel';
import type {SurfaceView} from './types';

function view(state: SurfaceView['selected_state']): SurfaceView {
  return {
    selected_state: state,
    frame: 0,
    sessions: [],
    available_actions: [],
    overflow_count: 0,
    activity_motion: false,
  };
}

describe('compileVisualFrame', () => {
  it('renders Ready as a dim dash, not a question', () => {
    const source = view('idle');
    source.sessions = [{slot: 2, state: 'idle', selected: true, accent: 'lime', label: 'Reviewer'}];
    const frame = compileVisualFrame(source);
    expect(frame.state.flat().filter(token => token !== 'off')).toEqual(Array(3).fill('state:idle:primary'));
    expect(frame.statuses[2]).toBe('state:idle:summary');
    expect(frame.selectors[2]).toBe('accent:lime:selected');
    expect(Object.values(frame.actions)).toEqual(Array(4).fill('off'));
  });

  it('renders the protocol question mark', () => {
    const frame = compileVisualFrame(view('waiting_for_reply'));
    const lit = frame.state.flat().filter((token) => token !== 'off');
    expect(lit).toHaveLength(14);
    expect(frame.state[7][3]).toBe('state:waiting_for_reply:primary');
  });

  it('keeps unavailable actions dark', () => {
    const source = view('waiting_for_approval');
    source.available_actions = ['approve', 'reject'];
    const frame = compileVisualFrame(source);
    expect(frame.actions.approve).toBe('action:approve:enabled');
    expect(frame.actions.reject).toBe('action:reject:enabled');
    expect(frame.actions.stop).toBe('off');
  });

  it('separates identity from state', () => {
    const source = view('running');
    source.sessions = [{
      slot: 1,
      state: 'error',
      selected: true,
      accent: 'magenta',
      label: 'Reviewer',
    }];
    const frame = compileVisualFrame(source);
    expect(frame.selectors[1]).toBe('accent:magenta:selected');
    expect(frame.statuses[1]).toBe('state:error:summary');
  });
});
