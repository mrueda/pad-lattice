import {describe, expect, it} from 'vitest';
import {compileVisualFrame} from './surfaceModel';
import {createPlaygroundState, nextPlaygroundEvent, playgroundReducer as reduce, playgroundScenarios, playgroundView, type PlaygroundState} from './playground';
import type {ControlAction} from './types';

const select = (state: PlaygroundState, slot: number) => reduce(state, {type: 'select', slot, expectedRevision: state.revision});
const act = (state: PlaygroundState, action: ControlAction) => reduce(state, {type: 'action', action, expectedRevision: state.revision});

describe('isolated playground scenarios', () => {
  it('only changes the selected session and resumes work rather than inventing success', () => {
    let state = select(createPlaygroundState(), 1);
    const others = state.sessions.filter((item) => item.slot !== 1);
    state = act(state, 'approve');
    expect(state.sessions[1].state).toBe('running');
    expect(playgroundView(state).available_actions).toEqual(['stop']);
    expect(state.sessions.filter((item) => item.slot !== 1)).toEqual(others);
    state = select(state, 2);
    state = act(state, 'retry');
    expect(state.sessions[2].state).toBe('running');
  });

  it('rejects duplicate, stale, and retargeted presses', () => {
    const initial = createPlaygroundState('resolved');
    const press = {type: 'action', action: 'approve', expectedRevision: initial.revision} as const;
    const accepted = reduce(initial, press);
    const repeated = reduce(accepted, press);
    expect(repeated.sessions).toEqual(accepted.sessions);
    expect(repeated.history.at(-1)?.blocked).toBe(true);
    const switched = select(initial, 0);
    expect(reduce(switched, press).sessions).toEqual(switched.sessions);
    const resolved = reduce(initial, {type: 'advance'});
    expect(reduce(resolved, press).sessions).toEqual(resolved.sessions);
    expect(act(resolved, 'approve').history.at(-1)?.blocked).toBe(true);
  });

  it('clears a disconnected target without selecting another session', () => {
    let state = createPlaygroundState('disconnect');
    state = reduce(state, {type: 'advance'});
    expect(state.sessions.map((item) => item.slot)).toEqual([0, 2]);
    expect(playgroundView(state)).toMatchObject({selected_state: null, available_actions: []});
    const frame = compileVisualFrame(playgroundView(state));
    expect(frame.selectors[1]).toBe('off');
    expect(Object.values(frame.actions).every((token) => token === 'off')).toBe(true);
    const background = reduce(state, {type: 'advance'});
    expect(playgroundView(background).available_actions).toEqual([]);
    expect(playgroundView(select(background, 0)).available_actions).toEqual(['approve', 'reject']);
  });

  it('does not steal selection on background changes or manual state edits', () => {
    let state = select(createPlaygroundState(), 2);
    state = reduce(state, {type: 'advance'});
    state = reduce(state, {type: 'set_state', slot: 1, state: 'success'});
    expect(state.sessions.find((item) => item.selected)?.slot).toBe(2);
    expect(playgroundView(state).selected_state).toBe('error');
    expect(reduce(state, {type: 'select', slot: 7, expectedRevision: state.revision})).toBe(state);
    expect(reduce(state, {type: 'set_state', slot: 7, state: 'error'})).toBe(state);
  });

  it('preserves monotonic revisions across scenario reset and selection', () => {
    let state = createPlaygroundState('resolved');
    const queued = {type: 'action', action: 'approve', expectedRevision: state.revision} as const;
    state = reduce(state, {type: 'reset'});
    expect(reduce(state, queued).sessions).toEqual(state.sessions);
    const revision = state.revision;
    state = reduce(state, {type: 'scenario', id: 'vocabulary'});
    expect(state.revision).toBeGreaterThan(revision);
    expect(state.sessions).toHaveLength(8);
  });

  it.each(playgroundScenarios)('replays $id deterministically without mutating its fixture', (scenario) => {
    const original = JSON.stringify(scenario);
    const run = () => {
      let state = createPlaygroundState(scenario.id);
      while (nextPlaygroundEvent(state)) state = reduce(state, {type: 'advance'});
      expect(reduce(state, {type: 'advance'})).toBe(state);
      return state;
    };
    expect(run()).toEqual(run());
    expect(JSON.stringify(scenario)).toBe(original);
    expect(createPlaygroundState(scenario.id).step).toBe(0);
  });

  it('bounds history and safely rejects unavailable actions', () => {
    let state = createPlaygroundState();
    const sessions = state.sessions;
    for (let i = 0; i < 30; i++) state = act(state, 'approve');
    expect(state.sessions).toEqual(sessions);
    expect(state.history).toHaveLength(6);
    expect(new Set(state.history.map((item) => item.id)).size).toBe(6);
  });
});
