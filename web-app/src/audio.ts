import {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import type {ExperienceStateMessage} from './types';

const defaultSoundtrackUrl = './experiences/audio/constellation-v1.wav';

export interface AudioOutput {
  enabled: boolean;
  toggle: () => void;
  playCue: (cue: string | null, slot: number | null, sequence: number) => void;
  syncExperience: (experience: ExperienceStateMessage | null) => void;
  stop: () => void;
}

export function useAudioOutput(): AudioOutput {
  const [enabled, setEnabled] = useState(false);
  const enabledRef = useRef(false);
  const soundtrackRef = useRef<HTMLAudioElement | null>(null);
  const timerRef = useRef<number | null>(null);
  const lastCueRef = useRef(0);
  const soundtrackUrlRef = useRef(defaultSoundtrackUrl);

  const stop = useCallback(() => {
    if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    timerRef.current = null;
    if (soundtrackRef.current) {
      soundtrackRef.current.pause();
      soundtrackRef.current.currentTime = 0;
    }
  }, []);

  const toggle = useCallback(() => {
    const next = !enabledRef.current;
    enabledRef.current = next;
    setEnabled(next);
    if (!next) {
      stop();
      return;
    }
    const soundtrack = soundtrackRef.current ?? new Audio(soundtrackUrlRef.current);
    soundtrack.preload = 'auto';
    soundtrack.preservesPitch = true;
    soundtrackRef.current = soundtrack;
    const previousVolume = soundtrack.volume;
    soundtrack.volume = 0;
    void soundtrack.play().then(() => {
      soundtrack.pause();
      soundtrack.currentTime = 0;
      soundtrack.volume = previousVolume;
    }).catch(() => {
      soundtrack.volume = previousVolume;
    });
  }, [stop]);

  const playCue = useCallback((cue: string | null, slot: number | null, sequence: number) => {
    if (sequence < lastCueRef.current) lastCueRef.current = 0;
    if (!enabledRef.current || !cue || sequence <= lastCueRef.current) return;
    lastCueRef.current = sequence;
    const suffix = slot === null ? 'none' : String(slot);
    const audio = new Audio(`./experiences/audio/earcon-${cue}-${suffix}.wav`);
    void audio.play().catch(() => undefined);
  }, []);

  const syncExperience = useCallback((experience: ExperienceStateMessage | null) => {
    if (!enabledRef.current || !experience || experience.kind !== 'show') {
      if (!experience || experience.status === 'idle' || experience.status === 'blocked') stop();
      return;
    }
    const soundtrackUrl = experience.audio_asset
      ? `./${experience.audio_asset.replace(/^\.\//, '')}`
      : defaultSoundtrackUrl;
    if (soundtrackUrlRef.current !== soundtrackUrl) {
      stop();
      soundtrackRef.current = null;
      soundtrackUrlRef.current = soundtrackUrl;
    }
    const soundtrack = soundtrackRef.current ?? new Audio(soundtrackUrl);
    soundtrackRef.current = soundtrack;
    soundtrack.preservesPitch = true;
    soundtrack.playbackRate = experience.tempo;
    const offset = Math.max(0, experience.elapsed_ms / 1000);
    if (experience.status === 'starting') {
      stop();
      soundtrack.currentTime = 0;
      timerRef.current = window.setTimeout(() => {
        timerRef.current = null;
        if (enabledRef.current) void soundtrack.play().catch(() => undefined);
      }, experience.start_delay_ms);
      return;
    }
    if (experience.status === 'playing') {
      const drift = Math.abs(soundtrack.currentTime - offset);
      if (soundtrack.paused || drift > 0.75) soundtrack.currentTime = offset;
      if (soundtrack.paused) void soundtrack.play().catch(() => undefined);
    }
  }, [stop]);

  useEffect(() => stop, [stop]);
  return useMemo(
    () => ({enabled, toggle, playCue, syncExperience, stop}),
    [enabled, playCue, stop, syncExperience, toggle],
  );
}
