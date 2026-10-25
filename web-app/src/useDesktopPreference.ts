import {useCallback, useEffect, useRef, useState} from 'react';
import {desktopRequest, isDesktop} from './desktop';

export function useDesktopPreference(key: 'pad_focused' | 'audio_enabled') {
  const [value, setValue] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const touched = useRef(false);
  const revision = useRef(0);
  useEffect(() => {
    if (!isDesktop()) return;
    let disposed = false;
    desktopRequest<Record<string, unknown>>('settings').then(settings => {
      if (!disposed && !touched.current && typeof settings[key] === 'boolean') setValue(settings[key]);
    }).catch(reason => { if (!disposed) setError(`Could not load preferences: ${String(reason)}`); });
    return () => { disposed = true; };
  }, [key]);
  const save = useCallback((next: boolean) => {
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
