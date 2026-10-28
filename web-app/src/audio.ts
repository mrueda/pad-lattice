import {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import type {ExperienceStateMessage} from './types';
import {AudioAssets} from './audioAssets';
import {isDesktop} from './desktop';
import {useDesktopPreference} from './useDesktopPreference';

const defaultSoundtrackUrl = './experiences/audio/constellation-v1.wav';
const earcons = new Set(['question', 'approval', 'approve', 'reject', 'retry', 'stop',
  'success', 'error', 'cancelled', 'session_selected', 'unavailable']);

export interface AudioOutput {
  enabled: boolean;
  error: string | null;
  toggle: () => void;
  playCue: (cue: string | null, slot: number | null, sequence: number) => void;
  playLiveCue: (cue: string, slot: number | null) => void;
  syncExperience: (experience: ExperienceStateMessage | null) => void;
  stop: () => void;
}

export function useAudioOutput(): AudioOutput {
  const preference = useDesktopPreference('audio_enabled');
  const {value: enabled, save: setEnabled} = preference;
  const [error, setError] = useState<string | null>(null);
  const assetsRef = useRef<AudioAssets | null>(null);
  const epochRef = useRef(0);
  const activeCues = useRef(new Set<HTMLAudioElement>());
  const recentCue = useRef({key: '', time: -Infinity});
  const resolveSource = useCallback((path: string) => {
    assetsRef.current ??= new AudioAssets(isDesktop());
    return assetsRef.current.resolve(path);
  }, []);
  const reportError = useCallback((reason: unknown) => {
    if (enabledRef.current && !(reason instanceof DOMException && reason.name === 'AbortError')) {
      setError(`Audio unavailable: ${reason instanceof Error ? reason.message : String(reason)}`);
    }
  }, []);
  const enabledRef = useRef(false);
  useEffect(() => { enabledRef.current = enabled; }, [enabled]);
  const soundtrackRef = useRef<HTMLAudioElement | null>(null);
  const timerRef = useRef<number | null>(null);
  const lastCueRef = useRef(0);
  const soundtrackUrlRef = useRef(defaultSoundtrackUrl);

  const stop = useCallback(() => {
    epochRef.current += 1;
    for (const cue of activeCues.current) cue.pause();
    activeCues.current.clear();
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
    setError(null);
    if (!next) {
      stop();
      return;
    }
    if (isDesktop()) return;
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
    }).catch((reason: unknown) => {
      soundtrack.volume = previousVolume;
      reportError(reason);
    });
  }, [stop, reportError, setEnabled]);

  const playLiveCue = useCallback((cue: string, slot: number | null) => {
    if (!enabledRef.current || !earcons.has(cue)
      || (slot !== null && (!Number.isInteger(slot) || slot < 0 || slot > 7))) return;
    const key = `${cue}:${slot}`;
    const now = performance.now();
    if (recentCue.current.key === key && now - recentCue.current.time < 120) return;
    recentCue.current = {key, time: now};
    const suffix = slot === null ? 'none' : String(slot);
    const epoch = epochRef.current;
    void resolveSource(`./experiences/audio/earcon-${cue}-${suffix}.wav`).then((url) => {
      if (!enabledRef.current || epoch !== epochRef.current) return;
      if (activeCues.current.size >= 4) return;
      const player = new Audio(url);
      activeCues.current.add(player);
      const release = () => activeCues.current.delete(player);
      player.onended = release;
      player.onerror = release;
      return player.play().catch((reason: unknown) => { release(); throw reason; });
    }).catch(reportError);
  }, [resolveSource, reportError]);

  const playCue = useCallback((cue: string | null, slot: number | null, sequence: number) => {
    if (sequence < lastCueRef.current) lastCueRef.current = 0;
    if (!cue || sequence <= lastCueRef.current) return;
    lastCueRef.current = sequence;
    playLiveCue(cue, slot);
  }, [playLiveCue]);

  const syncExperience = useCallback((experience: ExperienceStateMessage | null) => {
    if (!experience || experience.status === 'idle' || experience.status === 'blocked'
        || experience.kind !== 'show' || !enabledRef.current) {
      stop();
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
    const epoch = epochRef.current;
    void resolveSource(soundtrackUrl).then((url) => {
      if (!enabledRef.current || epoch !== epochRef.current) return;
      const soundtrack = soundtrackRef.current ?? new Audio(url);
      soundtrackRef.current = soundtrack;
      soundtrack.preservesPitch = true;
      soundtrack.playbackRate = experience.tempo;
      const offset = Math.max(0, experience.elapsed_ms / 1000);
      if (experience.status === 'starting') {
        stop();
        const scheduledEpoch = epochRef.current;
        soundtrack.currentTime = 0;
        timerRef.current = window.setTimeout(() => {
          timerRef.current = null;
          if (enabledRef.current && scheduledEpoch === epochRef.current) void soundtrack.play().catch(reportError);
        }, experience.start_delay_ms);
        return;
      }
      if (experience.status === 'playing') {
        if (timerRef.current !== null) window.clearTimeout(timerRef.current);
        timerRef.current = null;
        const drift = Math.abs(soundtrack.currentTime - offset);
        if (soundtrack.paused || drift > 0.75) soundtrack.currentTime = offset;
        if (soundtrack.paused) void soundtrack.play().catch(reportError);
      }
    }).catch(reportError);
  }, [stop, resolveSource, reportError]);

  useEffect(() => () => {
    stop();
    assetsRef.current?.close();
    assetsRef.current = null;
  }, [stop]);
  return useMemo(
    () => ({enabled, error: error || preference.error, toggle, playCue, playLiveCue, syncExperience, stop}),
    [enabled, error, preference.error, playCue, playLiveCue, stop, syncExperience, toggle],
  );
}
