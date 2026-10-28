import {describe, expect, it} from 'vitest';
import {elapsedLabel} from './AttentionView';

describe('attention elapsed time', () => {
  it('uses bounded, compact units without negative durations', () => {
    expect(elapsedLabel(-2)).toBe('0s');
    expect(elapsedLabel(9.8)).toBe('9s');
    expect(elapsedLabel(62)).toBe('1m 2s');
    expect(elapsedLabel(3661)).toBe('1h 1m');
  });
});
