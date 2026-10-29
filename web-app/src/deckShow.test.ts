import {describe, expect, it} from 'vitest';
import {deckShowColors} from './deckShow';
import type {FullSurfaceFrame} from './types';

describe('15-key Show adaptation', () => {
  it('returns black before the first frame', () => {
    expect(deckShowColors(null)).toEqual(Array(15).fill('#000000'));
  });

  it('preserves the brightest source color in every region', () => {
    const grid = Array.from({length: 8}, () => Array(8).fill('#000000'));
    for (let y = 0; y < 3; y++) for (let x = 0; x < 5; x++) {
      grid[Math.floor(y * 8 / 3)][Math.floor(x * 8 / 5)] = `#${(32 + y * 5 + x).toString(16)}aa44`;
    }
    const frame: FullSurfaceFrame = {grid, top: Array(8).fill('#ffffff'), right: Array(8).fill('#ffffff')};
    expect(deckShowColors(frame)).toEqual(Array.from({length: 15}, (_, i) => `#${(32 + i).toString(16)}aa44`));
  });

  it('handles malformed frame colors without inventing a control', () => {
    const frame = {grid: [['not-a-color']], top: [], right: []} as FullSurfaceFrame;
    expect(deckShowColors(frame)).toEqual(Array(15).fill('#000000'));
  });

  it('supports Neo and XL dimensions', () => {
    expect(deckShowColors(null, 4, 2)).toEqual(Array(8).fill('#000000'));
    expect(deckShowColors(null, 8, 4)).toEqual(Array(32).fill('#000000'));
  });
});
