import {Play, Sparkles, Square, Volume2, VolumeX} from 'lucide-react';

export function ExperienceControls({
  kind = null,
  active,
  admin,
  canStart = true,
  audioEnabled = false,
  blockedReason = null,
  caption = null,
  detail = null,
  onAudio,
  onStartDemo = null,
  onStartShow,
  onStop,
}: {
  kind?: 'demo' | 'show' | null;
  active: boolean;
  admin: boolean;
  canStart?: boolean;
  audioEnabled?: boolean;
  blockedReason?: string | null;
  caption?: string | null;
  detail?: string | null;
  onAudio?: () => void;
  onStartDemo?: (() => void) | null;
  onStartShow: (() => void) | null;
  onStop: () => void;
}) {
  const AudioIcon = audioEnabled ? Volume2 : VolumeX;
  return (
    <section className="experiencePanel" aria-live="polite">
      <div className="sectionTitle"><span>{kind === 'demo' ? 'INTERACTIVE DEMO' : kind === 'show' ? 'VISUAL SHOW' : 'DEMO & SHOW'}</span><span>{active ? (kind === 'demo' ? 'IN PROGRESS' : 'PLAYING') : 'READY'}</span></div>
      {caption ? <p className="experienceCaption">{caption}</p> : null}
        {detail ? <p className="experienceDetail">{detail}</p> : null}
        {blockedReason ? <p className="experienceWarning">{blockedReason}</p> : null}
      <div className="experienceActions">
        {admin && !active && onStartDemo ? (
          <button className="primaryButton" disabled={!canStart} onClick={onStartDemo}>
            <Play aria-hidden="true" /> Start Demo
          </button>
        ) : null}
        {admin && !active && onStartShow ? (
          <button className="primaryButton" disabled={!canStart} onClick={onStartShow}>
            <Sparkles aria-hidden="true" /> Start Show
          </button>
        ) : null}
        {admin && active ? (
          <button className="primaryButton danger" onClick={onStop}>
            <Square aria-hidden="true" /> Stop
          </button>
        ) : null}
        {onAudio ? <button className="textButton" onClick={onAudio} aria-pressed={audioEnabled}>
          <AudioIcon aria-hidden="true" /> Sound {audioEnabled ? 'on' : 'off'}
        </button> : null}
      </div>
    </section>
  );
}
