import {describe, expect, it} from 'vitest';
import demoData from '../public/experiences/demo-v1.json';
import performanceData from '../public/experiences/constellation-v1.json';
import {
  cueIndexAt,
  parseDemoManifest,
  parsePerformanceManifest,
  performanceCaptionAt,
  performanceFrame,
} from './experiences';

describe('shared experience assets', () => {
  it('loads the version-one Demo graph', () => {
    const demo = parseDemoManifest(demoData);
    expect(demo.initial_stage).toBe('select_reviewer');
    expect(demo.stages).toHaveLength(6);
  });

  it('maps the performance timeline to exact full-surface RGB', () => {
    const performance = parsePerformanceManifest(performanceData);
    const frame = performanceFrame(performance, 0);

    expect(cueIndexAt(performance, 0)).toBe(0);
    expect(cueIndexAt(performance, performance.duration_ms - 1)).toBe(
      performance.cues.length - 1,
    );
    expect(frame.grid).toHaveLength(8);
    expect(frame.grid.every((row) => row.length === 8)).toBe(true);
    expect(frame.top).toHaveLength(8);
    expect(frame.right).toHaveLength(8);
    expect(frame.grid[0][0]).toMatch(/^#[0-9a-f]{6}$/);

    const question = performance.cues.findIndex((cue) => cue.caption === 'A question');
    expect(performanceCaptionAt(performance, question + 1)).toBe('A question');
    const idea = performance.cues.findIndex((cue) => cue.act === 1);
    expect(performanceCaptionAt(performance, idea)).toBe('An Idea');
  });
});
