import {useCallback, useEffect, useRef, useState} from 'react';
import {desktopRequest, isDesktop} from './desktop';

function usePreference<T>(key: string, initial: T, valid: (value: unknown) => value is T) {
  const [value, setValue] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  const touched = useRef(false);
  const revision = useRef(0);
  useEffect(() => {
    if (!isDesktop()) return;
    let disposed = false;
    desktopRequest<Record<string, unknown>>('settings').then(settings => {
      if (!disposed && !touched.current && valid(settings[key])) setValue(settings[key]);
    }).catch(reason => { if (!disposed) setError(`Could not load preferences: ${String(reason)}`); });
    return () => { disposed = true; };
  }, [key, valid]);
  const save = useCallback((next: T) => {
    touched.current = true;
    setValue(next);
    setError(null);
    const attempt = ++revision.current;
    if (isDesktop()) void desktopRequest('settings', {[key]: next}).catch(reason => {
      if (attempt === revision.current) setError(`Could not save preferences: ${String(reason)}`);
    });
  }, [key]);
  return {value, save, error};
}

const isBoolean = (value: unknown): value is boolean => typeof value === 'boolean';
export type SurfaceLayout = 'grid' | 'stream-deck' | 'stream-deck-xl' | 'stream-deck-neo';
const isSurfaceLayout = (value: unknown): value is SurfaceLayout =>
  value === 'grid' || value === 'stream-deck' || value === 'stream-deck-xl' || value === 'stream-deck-neo';

export function useDesktopPreference(key: 'pad_focused' | 'audio_enabled' | 'light_theme') {
  return usePreference(key, false, isBoolean);
}

export function useSurfacePreference() {
  return usePreference<SurfaceLayout>('surface_layout', 'grid', isSurfaceLayout);
}
