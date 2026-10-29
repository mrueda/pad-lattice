import type {FullSurfaceFrame} from './types';

// Keep the brightest source pixel in each region so sparse glyphs remain visible.
export function deckShowColors(frame: FullSurfaceFrame | null, columns = 5, rows = 3): string[] {
  return Array.from({length: columns * rows}, (_, index) => {
    const x = index % columns, y = Math.floor(index / columns);
    let best = '#000000', brightness = 0;
    for (let row = Math.floor(y * 8 / rows); row < Math.floor((y + 1) * 8 / rows); row++) {
      for (let column = Math.floor(x * 8 / columns); column < Math.floor((x + 1) * 8 / columns); column++) {
        const color = frame?.grid[row]?.[column];
        if (!color || !/^#[0-9a-f]{6}$/i.test(color)) continue;
        const r = parseInt(color.slice(1, 3), 16), g = parseInt(color.slice(3, 5), 16), b = parseInt(color.slice(5, 7), 16);
        const value = r * 0.2126 + g * 0.7152 + b * 0.0722;
        if (value > brightness) {best = color; brightness = value;}
      }
    }
    return best;
  });
}
