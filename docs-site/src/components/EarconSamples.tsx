import React, {useRef} from 'react';
import useBaseUrl from '@docusaurus/useBaseUrl';

const samples = [
  ['question', 'Waiting for reply'], ['approval', 'Waiting for approval'],
  ['approve', 'Approved'], ['reject', 'Rejected'], ['retry', 'Retry'],
  ['stop', 'Stop'], ['success', 'Success'], ['error', 'Error'],
  ['cancelled', 'Cancelled'], ['session_selected', 'Session selected'],
  ['unavailable', 'Unavailable action'],
];

export default function EarconSamples() {
  const base = useBaseUrl('/play/experiences/audio/');
  const playing = useRef<HTMLAudioElement | null>(null);
  return <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: '1rem'}}>
    {samples.map(([cue, label]) => <figure key={cue} style={{margin: 0, minWidth: 0}}>
      <figcaption><strong>{label}</strong></figcaption>
      <audio controls preload="none" aria-label={`Listen: ${label}`} style={{width: '100%'}}
        src={`${base}earcon-${cue}-0.wav`} onPlay={event => {
          if (playing.current && playing.current !== event.currentTarget) playing.current.pause();
          playing.current = event.currentTarget;
        }} />
    </figure>)}
  </div>;
}
