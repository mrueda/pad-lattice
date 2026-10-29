import {useEffect, useState} from 'react';
import {isDesktop} from './desktop';
import {Loading} from './AppFrame';
import {LiveApp} from './LiveApp';
import {PublicApp} from './PublicApp';

type AppMode = 'loading' | 'demo' | 'live';

export default function App() {
  const [mode, setMode] = useState<AppMode>('loading');
  useEffect(() => {
    if (isDesktop()) { setMode('live'); return; }
    fetch('./config.json', {cache: 'no-store'})
      .then((response) => response.json())
      .then((config: {mode?: string; protocol?: number}) => {
        setMode(config.mode === 'live' && config.protocol === 1 ? 'live' : 'demo');
      })
      .catch(() => setMode('demo'));
  }, []);

  if (mode === 'loading') return <Loading />;
  return mode === 'live' ? <LiveApp /> : <PublicApp />;
}
