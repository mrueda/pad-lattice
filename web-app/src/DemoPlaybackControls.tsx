import {Pause, Play, RotateCcw} from 'lucide-react';
import type {useDemoPlayback} from './demoPlayback';

const time = (milliseconds: number) => `0:${String(Math.floor(milliseconds / 1000)).padStart(2, '0')}`;

export function DemoPlaybackControls({playback, onTry}: {playback: ReturnType<typeof useDemoPlayback>; onTry: () => void}) {
  return <section className="demoPlayback" aria-label="Demo playback">
    <div className="demoPlaybackButtons">
      <span>{playback.finished ? 'DEMO COMPLETE' : playback.paused ? 'PAUSED' : 'AUTOPLAY DEMO'}</span>
      <button className="textButton" disabled={playback.finished} onClick={playback.toggle}
        aria-label={playback.paused ? 'Resume demo' : 'Pause demo'} title={playback.paused ? 'Resume demo' : 'Pause demo'}>
        {playback.paused ? <Play aria-hidden="true" /> : <Pause aria-hidden="true" />}
      </button>
      <button className="textButton" onClick={playback.replay} aria-label="Replay demo" title="Replay demo"><RotateCcw aria-hidden="true" /></button>
      <small>{time(playback.elapsed)} / {time(playback.duration)}</small>
    </div>
    <progress aria-label="Demo progress" value={playback.elapsed} max={playback.duration} />
    {playback.finished ? <button className="primaryButton demoTry" onClick={onTry}><Play aria-hidden="true" /> Try it yourself</button> : null}
  </section>;
}
