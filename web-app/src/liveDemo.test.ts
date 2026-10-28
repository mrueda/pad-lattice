import {describe, expect, it} from 'vitest';
import demoData from '../public/experiences/demo-v1.json';
import {parseDemoManifest} from './experiences';
import {demoGuide} from './liveDemo';
import type {ExperienceStateMessage, SurfaceView} from './types';

const manifest = parseDemoManifest(demoData);

function stage(index: number) {
  const experience: ExperienceStateMessage = {
    protocol: 1, type: 'experience_state', kind: 'demo', status: 'playing',
    title: manifest.title, cue_index: index, caption: null, detail: null,
    elapsed_ms: 0, duration_ms: null, tempo: 1, audio_asset: null,
    audio_cue: null, audio_slot: null, audio_sequence: 0, start_delay_ms: 0, reason: null,
  };
  const view: SurfaceView = {
    ...structuredClone(manifest.stages[index].view),
    selected_state: null, control_revision: 1, frame: 0, overflow_count: 0, activity_motion: false,
  };
  return {experience, view};
}

describe('live demo guidance', () => {
  it('identifies the requested scene and action from the shared manifest', () => {
    const selection = stage(0);
    expect(demoGuide(manifest, selection.experience, selection.view)?.label).toBe('Select Reviewer');
    const action = stage(1);
    expect(demoGuide(manifest, action.experience, action.view)?.label).toBe('Approve Reviewer');
  });

  it('does not guide a stopped, unavailable, or different experience', () => {
    const {experience, view} = stage(0);
    expect(demoGuide(null, experience, view)).toBeNull();
    expect(demoGuide(manifest, {...experience, status: 'idle'}, view)).toBeNull();
    expect(demoGuide(manifest, {...experience, kind: 'show'}, view)).toBeNull();
    for (const cue_index of [-1, 0.5, 999, null]) {
      expect(demoGuide(manifest, {...experience, cue_index}, view)).toBeNull();
    }
  });

  it('waits for a matching surface snapshot', () => {
    const {experience, view} = stage(0);
    view.sessions[0].label = 'Different chat';
    expect(demoGuide(manifest, experience, view)).toBeNull();
  });

  it('does not suggest unavailable actions or actions on the wrong session', () => {
    const {experience, view} = stage(1);
    expect(demoGuide(manifest, experience, {...view, available_actions: []})).toBeNull();
    view.sessions.forEach(session => {session.selected = session.slot === 0;});
    expect(demoGuide(manifest, experience, view)).toBeNull();
  });
});
