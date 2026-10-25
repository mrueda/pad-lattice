import {afterEach, describe, expect, it, vi} from 'vitest';
import {AudioAssets} from './audioAssets';

afterEach(() => vi.restoreAllMocks());

describe('audio asset URLs', () => {
  it('keeps ordinary browser URLs unchanged', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch');
    expect(await new AudioAssets(false).resolve('./cue.wav')).toBe('./cue.wav');
    expect(fetch).not.toHaveBeenCalled();
  });

  it('fetches desktop audio once and revokes its blob on close', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('wave'));
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:audio');
    const revoke = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    const assets = new AudioAssets(true);
    expect(await Promise.all([assets.resolve('./cue.wav'), assets.resolve('./cue.wav')]))
      .toEqual(['blob:audio', 'blob:audio']);
    expect(fetch).toHaveBeenCalledTimes(1);
    assets.close();
    expect(revoke).toHaveBeenCalledWith('blob:audio');
    await expect(assets.resolve('./cue.wav')).rejects.toThrow('closed');
  });

  it('reports missing audio and allows a later retry', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('', {status: 404}));
    const assets = new AudioAssets(true);
    await expect(assets.resolve('./cue.wav')).rejects.toThrow('404');
    await expect(assets.resolve('./cue.wav')).rejects.toThrow('404');
    expect(fetch).toHaveBeenCalledTimes(2);
  });
});
