"""Dependency-free audio feedback and authored show scoring."""

from __future__ import annotations

import math
import random
import shutil
import subprocess
import sys
import tempfile
import time
import wave
from array import array
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol

SAMPLE_RATE = 22_050
SESSION_INTERVALS = (0, 2, 4, 5, 7, 9, 11, 12)
REFERENCE_SCORE_BEATS = 64
REFERENCE_SCORE_KEY = "B-flat minor"
B_FLAT_MINOR_PITCH_CLASSES = frozenset({0, 1, 3, 5, 6, 8, 10})
REFERENCE_SCORE_MAX_POLYPHONY = 6
REFERENCE_SCORE_MAX_ONSETS = 48
REFERENCE_SCORE_MIN_PIANO_SPACE = 0.24
REFERENCE_SCORE_STRING_CHORDS = 12
ROBOT_SIGNATURE_TEXT = "PAD LATTICE"
ROBOT_GREETING_TEXT = "HELLO FROM CODEX CLI"
SCORE_CAPTIONS = frozenset(
    {
        "Alone",
        "An idea",
        "A question",
        "The search",
        "A friend",
        "A connection",
        "Hope",
        "The storm",
        "Loss",
        "Courage",
        "A call",
        "An answer",
        "A community",
        "Together, a solution",
        "Joy",
        "A constellation",
        "Pad-Lattice",
        "No light alone",
    }
)


class Earcon(str, Enum):
    """Short semantic sounds used by the control plane."""

    QUESTION = "question"
    APPROVAL = "approval"
    APPROVE = "approve"
    REJECT = "reject"
    RETRY = "retry"
    STOP = "stop"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"
    SESSION_SELECTED = "session_selected"
    UNAVAILABLE = "unavailable"


EARCON_DESCRIPTIONS: Mapping[Earcon, str] = {
    Earcon.QUESTION: "gentle rising question",
    Earcon.APPROVAL: "two unresolved knocks",
    Earcon.APPROVE: "short rising confirmation",
    Earcon.REJECT: "short descending refusal",
    Earcon.RETRY: "three-note restart",
    Earcon.STOP: "firm falling stop",
    Earcon.SUCCESS: "bright major chime",
    Earcon.ERROR: "low dissonant descent",
    Earcon.CANCELLED: "two muted low notes",
    Earcon.SESSION_SELECTED: "session-specific bell",
    Earcon.UNAVAILABLE: "muted unavailable click",
}


class AudioFeedback(Protocol):
    """Optional nonblocking semantic-audio output."""

    def play(self, cue: Earcon, *, slot: int | None = None) -> None: ...

    def close(self) -> None: ...


class Soundtrack(Protocol):
    """One running show soundtrack."""

    def close(self) -> None: ...


class AudioUnavailableError(ValueError):
    """Raised when explicit audio was requested without a usable player."""


@dataclass(frozen=True)
class StoryBeat:
    """One visual cue positioned on the soundtrack timeline."""

    act: str
    caption: str | None
    start: float
    duration: float


@dataclass(frozen=True)
class _Tone:
    start: float
    duration: float
    note: float
    volume: float = 0.2
    voice: str = "warm"
    pan: float = 0.0
    space: float = 0.0


@dataclass(frozen=True)
class _Noise:
    start: float
    duration: float
    volume: float = 0.08
    seed: int = 1
    pan: float = 0.0
    space: float = 0.0


@dataclass(frozen=True)
class _RobotSpeech:
    start: float
    duration: float
    text: str
    volume: float = 0.28


@dataclass
class _ProcessSoundtrack:
    process: subprocess.Popen[bytes]
    path: Path

    def close(self) -> None:
        _stop_process(self.process)
        self.path.unlink(missing_ok=True)


class SystemAudioFeedback:
    """Render cached earcons through an available operating-system player."""

    def __init__(
        self,
        *,
        player: Sequence[str] | None = None,
        popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._player = tuple(player) if player is not None else find_audio_player()
        self._popen = popen
        self._clock = clock
        self._directory = tempfile.TemporaryDirectory(prefix="pad-lattice-audio-")
        self._paths: dict[tuple[Earcon, int | None], Path] = {}
        self._speech_paths: dict[tuple[str, float], Path] = {}
        self._processes: list[subprocess.Popen[bytes]] = []
        self._last_played: dict[tuple[Earcon, int | None], float] = {}
        self._last_spoken: dict[tuple[str, float], float] = {}
        self._closed = False

    def play(self, cue: Earcon, *, slot: int | None = None) -> None:
        if self._closed:
            return
        normalized_slot = _normalized_slot(slot)
        key = (cue, normalized_slot)
        now = self._clock()
        last_played = self._last_played.get(key)
        if last_played is not None and now - last_played < 0.12:
            return
        self._last_played[key] = now
        self._reap()
        while len(self._processes) >= 4:
            _stop_process(self._processes.pop(0))
        path = self._paths.get(key)
        if path is None:
            slot_label = normalized_slot if normalized_slot is not None else "none"
            path = Path(self._directory.name) / (
                f"{cue.value}-{slot_label}.wav"
            )
            _write_earcon(path, cue, normalized_slot)
            self._paths[key] = path
        self._processes.append(_spawn(self._player, path, popen=self._popen))

    def speak(self, text: str, *, duration: float | None = None) -> None:
        """Speak one supported phrase without blocking MIDI rendering."""

        if self._closed:
            return
        normalized = " ".join(text.upper().split())
        selected_duration = (
            _robot_phrase_duration(normalized) if duration is None else duration
        )
        if selected_duration <= 0:
            raise ValueError("robot phrase duration must be positive")
        key = (normalized, round(selected_duration, 6))
        now = self._clock()
        last_spoken = self._last_spoken.get(key)
        if last_spoken is not None and now - last_spoken < 0.12:
            return
        self._last_spoken[key] = now
        self._reap()
        while len(self._processes) >= 4:
            _stop_process(self._processes.pop(0))
        path = self._speech_paths.get(key)
        if path is None:
            path = Path(self._directory.name) / f"speech-{len(self._speech_paths)}.wav"
            _write_robot_speech(path, normalized, selected_duration)
            self._speech_paths[key] = path
        self._processes.append(_spawn(self._player, path, popen=self._popen))

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for process in self._processes:
            _stop_process(process)
        self._processes.clear()
        self._directory.cleanup()

    def _reap(self) -> None:
        self._processes = [
            process for process in self._processes if process.poll() is None
        ]


def find_audio_player() -> tuple[str, ...]:
    """Return the first supported system WAV player command."""

    candidates = (
        ("pw-play",),
        ("paplay",),
        ("aplay", "-q"),
        ("afplay",),
        ("ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"),
    )
    for command in candidates:
        executable = shutil.which(command[0])
        if executable is not None:
            return (executable, *command[1:])
    raise AudioUnavailableError(
        "audio requested, but no supported player was found "
        "(pw-play, paplay, aplay, afplay, or ffplay)"
    )


def start_constellation_soundtrack(
    timeline: Sequence[StoryBeat],
    *,
    player: Sequence[str] | None = None,
    popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
) -> Soundtrack:
    """Synthesize and start the score for the reference visual story."""

    if not timeline:
        raise ValueError("soundtrack timeline must contain at least one beat")
    command = tuple(player) if player is not None else find_audio_player()
    duration = max(beat.start + beat.duration for beat in timeline)
    acts = _act_windows(timeline)
    if len(acts) != 8:
        raise ValueError("reference soundtrack requires eight ordered acts")
    captions = {beat.caption for beat in timeline if beat.caption is not None}
    missing_captions = SCORE_CAPTIONS - captions
    if missing_captions:
        missing = ", ".join(sorted(missing_captions))
        raise ValueError(f"reference soundtrack is missing story cues: {missing}")
    tones, noises, speeches = _constellation_score(timeline, duration)
    temporary = tempfile.NamedTemporaryFile(
        prefix="pad-lattice-show-",
        suffix=".wav",
        delete=False,
    )
    path = Path(temporary.name)
    temporary.close()
    try:
        _write_stereo_wav(
            path,
            duration,
            tones,
            noises,
            speeches,
            beat_length=(duration - timeline[0].start) / REFERENCE_SCORE_BEATS,
        )
        process = _spawn(command, path, popen=popen)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return _ProcessSoundtrack(process, path)


def _act_windows(timeline: Sequence[StoryBeat]) -> tuple[tuple[float, float], ...]:
    ordered: list[tuple[str, float, float]] = []
    for beat in timeline:
        end = beat.start + beat.duration
        if ordered and ordered[-1][0] == beat.act:
            name, start, _ = ordered[-1]
            ordered[-1] = (name, start, end)
        else:
            ordered.append((beat.act, beat.start, end))
    return tuple((start, end) for _, start, end in ordered)


def _constellation_score(
    timeline: Sequence[StoryBeat],
    duration: float,
) -> tuple[tuple[_Tone, ...], tuple[_Noise, ...], tuple[_RobotSpeech, ...]]:
    """Compose a sparse original piano-and-strings score in B-flat minor."""

    tones: list[_Tone] = []
    noises: list[_Noise] = []
    speeches: list[_RobotSpeech] = []
    acts = _act_windows(timeline)
    marks = {
        beat.caption: beat.start
        for beat in timeline
        if beat.caption is not None
    }
    origin = acts[0][0]
    beat_length = (duration - origin) / REFERENCE_SCORE_BEATS

    def at(reference_beat: float) -> float:
        return origin + reference_beat * beat_length

    def add(
        start: float,
        midi_note: float,
        beats: float,
        volume: float,
        voice: str = "piano",
        pan: float = 0.0,
        space: float = 0.5,
    ) -> None:
        if start >= duration:
            return
        note_duration = min(beats * beat_length, duration - start)
        tones.append(
            _Tone(
                start,
                max(0.05, note_duration),
                midi_note,
                volume,
                voice,
                pan,
                space,
            )
        )

    def phrase(
        start: float,
        notes: Sequence[tuple[float, float, float]],
        *,
        volume: float,
        pan: float = 0.0,
        space: float = 0.55,
    ) -> None:
        for offset, midi_note, length in notes:
            add(
                start + offset * beat_length,
                midi_note,
                length,
                volume,
                "piano",
                pan,
                space,
            )

    def string_chord(
        reference_beat: float,
        notes: Sequence[float],
        beats: float,
        *,
        volume: float,
    ) -> None:
        start = at(reference_beat)
        pans = (-0.42, 0.0, 0.42)
        for midi_note, pan in zip(notes, pans, strict=True):
            add(
                start,
                midi_note,
                beats,
                volume,
                "strings",
                pan,
                0.28,
            )

    # Long-short-long, then a quieter answer. The contour uses wide intervals
    # so the identity comes from rhythm and shape rather than scale motion.
    spark_motif = (
        (0.0, 70, 1.25),
        (1.35, 77, 0.75),
        (2.05, 73, 1.2),
        (3.3, 68, 1.15),
        (4.55, 72, 0.7),
        (5.2, 70, 1.5),
    )

    # Slow strings carry the harmony between scene changes. Wide voicings keep
    # the low register clear while the piano remains the narrative voice.
    harmony = (
        (4.0, 4.0, (46, 53, 61), 0.036),   # B-flat minor
        (8.0, 4.0, (44, 53, 61), 0.034),   # D-flat / A-flat
        (12.0, 2.0, (42, 49, 58), 0.035),  # G-flat
        (14.0, 2.0, (41, 48, 58), 0.034),  # Fsus
        (16.0, 8.0, (46, 53, 61), 0.036),  # B-flat minor
        (24.0, 8.0, (39, 46, 54), 0.039),  # E-flat minor
        (32.0, 8.0, (46, 53, 61), 0.037),  # B-flat minor
        (40.0, 8.0, (42, 49, 58), 0.039),  # G-flat
        (48.0, 4.0, (46, 53, 61), 0.041),  # B-flat minor
        (52.0, 4.0, (42, 49, 58), 0.042),  # G-flat
        (56.0, 4.0, (41, 48, 58), 0.043),  # Fsus
        (60.0, 4.0, (46, 53, 61), 0.042),  # B-flat minor
    )
    for chord_start, chord_beats, chord_notes, chord_volume in harmony:
        string_chord(
            chord_start,
            chord_notes,
            chord_beats,
            volume=chord_volume,
        )

    # Alone becomes the first statement of the theme.
    add(at(1.15), 70, 2.4, 0.18, "piano", -0.12, 0.7)
    add(at(2.7), 46, 1.0, 0.035, "cello", 0.0, 0.45)
    phrase(
        marks["An idea"],
        spark_motif,
        volume=0.135,
        pan=-0.08,
    )

    # Two voices meet without overlapping harmonic extensions.
    phrase(
        at(16.15),
        ((0.0, 70, 1.05), (1.35, 77, 0.75)),
        volume=0.105,
        pan=-0.6,
    )
    phrase(
        marks["A friend"],
        ((0.0, 73, 1.05), (1.35, 70, 0.9)),
        volume=0.1,
        pan=0.6,
    )

    # The storm breaks the motif into E-flat-minor chord tones. A restrained
    # noise layer adds weather without introducing another pitched voice.
    phrase(
        marks["The storm"],
        ((0.0, 70, 0.9), (1.1, 66, 1.0)),
        volume=0.115,
        pan=-0.18,
        space=0.55,
    )
    add(marks["Loss"], 39, 3.0, 0.05, "cello", 0.0, 0.5)
    noises.append(_Noise(at(24.0), 4.0 * beat_length, 0.024, 41, 0.0, 0.7))
    add(marks["Courage"], 65, 1.1, 0.115, "piano", -0.12)

    # The call restates the opening leap. Four replies are enough to imply the
    # wider visual community without spelling out every entrance in sound.
    phrase(
        marks["A call"],
        spark_motif[:2],
        volume=0.105,
        pan=-0.25,
        space=0.55,
    )
    answer_start = marks["An answer"]
    replies = (70, 77, 73, 82)
    reply_pans = (-0.75, 0.75, -0.35, 0.35)
    for index, (midi_note, pan) in enumerate(zip(replies, reply_pans)):
        add(
            answer_start + index * 1.1 * beat_length,
            midi_note,
            0.82,
            0.075,
            "piano",
            pan,
            0.55,
        )

    # The together phrase rises through the sustained community harmony.
    phrase(
        marks["Together, a solution"],
        ((0.0, 70, 1.05), (1.35, 77, 0.9)),
        volume=0.1,
        pan=0.0,
        space=0.55,
    )

    # The complete motif returns over Fsus and resolves after the bass reaches
    # B-flat. One low cello note is the only added weight in the final image.
    phrase(
        marks["Pad-Lattice"],
        spark_motif,
        volume=0.145,
        pan=0.0,
        space=0.24,
    )
    add(marks["No light alone"], 46, 2.0, 0.045, "cello", 0.0, 0.5)
    signature_start = at(60.55)
    speeches.append(
        _RobotSpeech(
            signature_start,
            min(2.55 * beat_length, duration - signature_start),
            ROBOT_SIGNATURE_TEXT,
        )
    )
    return tuple(tones), tuple(noises), tuple(speeches)



def _write_earcon(path: Path, cue: Earcon, slot: int | None) -> None:
    root = 60 + SESSION_INTERVALS[slot] if slot is not None else 60
    patterns: dict[Earcon, tuple[_Tone, ...]] = {
        Earcon.QUESTION: (
            _Tone(0.0, 0.24, root, 0.22, "bell"),
            _Tone(0.2, 0.38, root + 7, 0.24, "bell"),
        ),
        Earcon.APPROVAL: (
            _Tone(0.0, 0.22, root, 0.2, "bell"),
            _Tone(0.0, 0.22, root + 6, 0.12, "bell"),
            _Tone(0.3, 0.3, root, 0.2, "bell"),
            _Tone(0.3, 0.3, root + 6, 0.12, "bell"),
        ),
        Earcon.APPROVE: tuple(
            _Tone(index * 0.09, 0.28, root + interval, 0.2, "bell")
            for index, interval in enumerate((0, 4, 7))
        ),
        Earcon.REJECT: (
            _Tone(0.0, 0.28, root + 3, 0.2, "bell"),
            _Tone(0.18, 0.38, root - 2, 0.22, "dark"),
        ),
        Earcon.RETRY: tuple(
            _Tone(index * 0.11, 0.25, root + interval, 0.18, "bell")
            for index, interval in enumerate((0, 2, 4))
        ),
        Earcon.STOP: (
            _Tone(0.0, 0.2, root, 0.22, "dark"),
            _Tone(0.14, 0.36, root - 12, 0.24, "dark"),
        ),
        Earcon.SUCCESS: tuple(
            _Tone(index * 0.1, 0.42, root + interval, 0.2, "bell")
            for index, interval in enumerate((0, 4, 7, 12))
        ),
        Earcon.ERROR: (
            _Tone(0.0, 0.3, root, 0.2, "dark"),
            _Tone(0.12, 0.38, root - 1, 0.18, "dark"),
            _Tone(0.28, 0.4, root - 7, 0.22, "dark"),
        ),
        Earcon.CANCELLED: (
            _Tone(0.0, 0.16, root - 12, 0.18, "dark"),
            _Tone(0.24, 0.2, root - 12, 0.16, "dark"),
        ),
        Earcon.SESSION_SELECTED: (_Tone(0.0, 0.5, root + 12, 0.22, "bell"),),
        Earcon.UNAVAILABLE: (_Tone(0.0, 0.14, root - 18, 0.13, "dark"),),
    }
    tones = patterns[cue]
    duration = max(tone.start + tone.duration for tone in tones) + 0.04
    _write_wav(path, duration, tones, ())


def _write_wav(
    path: Path,
    duration: float,
    tones: Sequence[_Tone],
    noises: Sequence[_Noise],
) -> None:
    sample_count = max(1, math.ceil(duration * SAMPLE_RATE))
    samples = array("f", [0.0]) * sample_count
    for tone in tones:
        _mix_tone(samples, tone)
    for noise in noises:
        _mix_noise(samples, noise)
    _write_mono_samples(path, samples)


def _write_robot_speech(path: Path, text: str, duration: float) -> None:
    rendered = _render_robot_phrase(text, duration)
    samples = array("f", (sample * 0.36 for sample in rendered))
    _write_mono_samples(path, samples)


def _write_mono_samples(path: Path, samples: array[float]) -> None:
    peak = max((abs(sample) for sample in samples), default=1.0)
    gain = 0.78 / max(1.0, peak)
    pcm = array(
        "h",
        (
            max(-32768, min(32767, round(sample * gain * 32767)))
            for sample in samples
        ),
    )
    if sys.byteorder == "big":
        pcm.byteswap()
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(pcm.tobytes())


def _write_stereo_wav(
    path: Path,
    duration: float,
    tones: Sequence[_Tone],
    noises: Sequence[_Noise],
    speeches: Sequence[_RobotSpeech] = (),
    *,
    beat_length: float,
) -> None:
    sample_count = max(1, math.ceil(duration * SAMPLE_RATE))
    left = array("f", [0.0]) * sample_count
    right = array("f", [0.0]) * sample_count
    space_left = array("f", [0.0]) * sample_count
    space_right = array("f", [0.0]) * sample_count
    for tone in tones:
        angle = (max(-1.0, min(1.0, tone.pan)) + 1.0) * math.pi / 4.0
        _mix_tone(
            left,
            tone,
            gain=math.cos(angle),
            secondary_samples=right,
            secondary_gain=math.sin(angle),
        )
        if tone.space > 0:
            _mix_tone(
                space_left,
                tone,
                gain=math.cos(angle) * tone.space,
                secondary_samples=space_right,
                secondary_gain=math.sin(angle) * tone.space,
            )
    for noise in noises:
        angle = (max(-1.0, min(1.0, noise.pan)) + 1.0) * math.pi / 4.0
        _mix_noise(
            left,
            noise,
            gain=math.cos(angle),
            secondary_samples=right,
            secondary_gain=math.sin(angle),
        )
        if noise.space > 0:
            _mix_noise(
                space_left,
                noise,
                gain=math.cos(angle) * noise.space,
                secondary_samples=space_right,
                secondary_gain=math.sin(angle) * noise.space,
            )
    effect_left, effect_right = _build_stereo_space(
        space_left,
        space_right,
        beat_length=beat_length,
    )
    for index in range(sample_count):
        left[index] += effect_left[index]
        right[index] += effect_right[index]

    for speech in speeches:
        _duck_stereo(left, right, speech)
        _mix_robot_speech(left, right, speech)

    fade_in = min(len(left), round(0.025 * SAMPLE_RATE))
    fade_out = min(len(left), round(0.55 * SAMPLE_RATE))
    for index in range(fade_in):
        factor = index / max(1, fade_in)
        left[index] *= factor
        right[index] *= factor
    for offset in range(fade_out):
        factor = (fade_out - offset) / max(1, fade_out)
        index = len(left) - fade_out + offset
        left[index] *= factor
        right[index] *= factor

    peak = max(
        max((abs(sample) for sample in left), default=1.0),
        max((abs(sample) for sample in right), default=1.0),
    )
    gain = 0.82 / max(1.0, peak)
    pcm = array("h")
    for left_sample, right_sample in zip(left, right):
        pcm.append(
            max(-32768, min(32767, round(left_sample * gain * 32767)))
        )
        pcm.append(
            max(-32768, min(32767, round(right_sample * gain * 32767)))
        )
    if sys.byteorder == "big":
        pcm.byteswap()
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(pcm.tobytes())


def _duck_stereo(
    left: array[float],
    right: array[float],
    speech: _RobotSpeech,
) -> None:
    start = max(0, round((speech.start - 0.16) * SAMPLE_RATE))
    speech_start = max(start, round(speech.start * SAMPLE_RATE))
    speech_end = min(len(left), round((speech.start + speech.duration) * SAMPLE_RATE))
    end = min(len(left), speech_end + round(0.2 * SAMPLE_RATE))
    floor = 0.58
    for index in range(start, end):
        if index < speech_start:
            progress = (index - start) / max(1, speech_start - start)
            factor = 1.0 - (1.0 - floor) * progress
        elif index < speech_end:
            factor = floor
        else:
            progress = (index - speech_end) / max(1, end - speech_end)
            factor = floor + (1.0 - floor) * progress
        left[index] *= factor
        right[index] *= factor


def _mix_robot_speech(
    left: array[float],
    right: array[float],
    speech: _RobotSpeech,
) -> None:
    rendered = _render_robot_phrase(speech.text, speech.duration)
    start = max(0, round(speech.start * SAMPLE_RATE))
    end = min(len(left), start + len(rendered))
    delay = round(0.043 * SAMPLE_RATE)
    center_gain = speech.volume / math.sqrt(2.0)
    for index in range(start, end):
        source = index - start
        sample = rendered[source] * center_gain
        left[index] += sample
        right[index] += sample
        if source >= delay:
            echo = rendered[source - delay] * speech.volume * 0.09
            left[index] += echo * 0.82
            right[index] += echo


def _render_robot_phrase(text: str, duration: float) -> array[float]:
    if duration <= 0:
        raise ValueError("robot phrase duration must be positive")

    normalized = " ".join(text.upper().split())
    segments = _robot_phrase_segments(normalized)
    total_weight = sum(segment[1] for segment in segments)
    target_samples = max(1, round(duration * SAMPLE_RATE))
    output = array("f")
    generator = random.Random(0x504C)
    elapsed_samples = 0

    for segment_index, (kind, weight, formants, f0, level) in enumerate(segments):
        if segment_index == len(segments) - 1:
            length = target_samples - len(output)
        else:
            length = max(1, round(target_samples * weight / total_weight))
        if kind == "silence":
            output.extend([0.0] * length)
        elif kind == "voiced" and formants is not None:
            output.extend(
                _render_robot_voiced(
                    length,
                    elapsed_samples,
                    f0=f0,
                    formants=formants,
                    level=level,
                )
            )
        else:
            output.extend(
                _render_robot_noise(
                    length,
                    kind=kind,
                    level=level,
                    generator=generator,
                )
            )
        elapsed_samples += length

    if len(output) > target_samples:
        del output[target_samples:]
    elif len(output) < target_samples:
        output.extend([0.0] * (target_samples - len(output)))

    # A low-rate sample hold gives the otherwise clean formants a vintage
    # speech-computer edge without making the consonants unintelligible.
    for index in range(0, len(output) - 1, 2):
        held = (output[index] + output[index + 1]) * 0.5
        output[index] = held
        output[index + 1] = held
    peak = max((abs(sample) for sample in output), default=1.0)
    if peak > 0:
        for index in range(len(output)):
            output[index] /= peak
    return output


def _robot_phrase_duration(text: str) -> float:
    normalized = " ".join(text.upper().split())
    durations = {
        ROBOT_SIGNATURE_TEXT: 1.6,
        ROBOT_GREETING_TEXT: 10.32,
    }
    try:
        return durations[normalized]
    except KeyError as exc:
        raise ValueError(f"unsupported robot phrase: {text}") from exc


def _robot_phrase_segments(
    text: str,
) -> tuple[tuple[str, float, Sequence[tuple[float, float, float]] | None, float, float], ...]:
    ae = ((660.0, 105.0, 1.0), (1720.0, 150.0, 0.72), (2410.0, 190.0, 0.4))
    ih = ((390.0, 90.0, 1.0), (1990.0, 155.0, 0.66), (2550.0, 190.0, 0.34))
    eh = ((530.0, 100.0, 1.0), (1840.0, 155.0, 0.7), (2480.0, 190.0, 0.35))
    ah = ((640.0, 115.0, 1.0), (1190.0, 155.0, 0.62), (2500.0, 210.0, 0.3))
    ow = ((450.0, 100.0, 1.0), (900.0, 145.0, 0.68), (2450.0, 210.0, 0.28))
    ee = ((270.0, 80.0, 1.0), (2290.0, 165.0, 0.75), (3010.0, 220.0, 0.3))
    liquid = ((410.0, 100.0, 1.0), (1180.0, 145.0, 0.52), (2650.0, 210.0, 0.24))
    rhotic = ((350.0, 100.0, 1.0), (1050.0, 145.0, 0.56), (1700.0, 180.0, 0.4))
    nasal = ((250.0, 80.0, 1.0), (1000.0, 130.0, 0.42), (2200.0, 190.0, 0.2))
    stop = ((350.0, 120.0, 1.0), (1650.0, 210.0, 0.42), (2700.0, 260.0, 0.2))

    signature = (
        ("silence", 0.045, None, 108.0, 0.0),
        ("burst", 0.05, None, 108.0, 0.5),
        ("voiced", 0.29, ae, 108.0, 1.0),
        ("voiced", 0.075, stop, 106.0, 0.58),
        ("burst", 0.025, None, 106.0, 0.34),
        ("silence", 0.12, None, 104.0, 0.0),
        ("voiced", 0.14, liquid, 104.0, 0.72),
        ("voiced", 0.265, ae, 104.0, 0.96),
        ("silence", 0.035, None, 102.0, 0.0),
        ("burst", 0.055, None, 102.0, 0.52),
        ("voiced", 0.16, ih, 102.0, 0.82),
        ("fricative", 0.22, None, 102.0, 0.56),
        ("silence", 0.03, None, 102.0, 0.0),
    )
    greeting = (
        # HELLO
        ("silence", 0.45, None, 110.0, 0.0),
        ("fricative", 0.07, None, 110.0, 0.28),
        ("voiced", 0.16, eh, 110.0, 0.82),
        ("voiced", 0.12, liquid, 109.0, 0.7),
        ("voiced", 0.23, ow, 108.0, 0.9),
        ("silence", 2.07, None, 108.0, 0.0),
        # FROM
        ("fricative", 0.1, None, 107.0, 0.42),
        ("voiced", 0.11, rhotic, 107.0, 0.66),
        ("voiced", 0.18, ah, 106.0, 0.86),
        ("voiced", 0.13, nasal, 105.0, 0.68),
        ("silence", 1.93, None, 105.0, 0.0),
        # CODEX
        ("silence", 0.025, None, 105.0, 0.0),
        ("burst", 0.045, None, 105.0, 0.48),
        ("voiced", 0.24, ow, 105.0, 0.92),
        ("voiced", 0.07, stop, 104.0, 0.55),
        ("burst", 0.02, None, 104.0, 0.28),
        ("voiced", 0.17, eh, 104.0, 0.86),
        ("silence", 0.02, None, 103.0, 0.0),
        ("burst", 0.04, None, 103.0, 0.46),
        ("fricative", 0.15, None, 103.0, 0.5),
        ("silence", 2.02, None, 103.0, 0.0),
        # C - L - I
        ("fricative", 0.12, None, 103.0, 0.5),
        ("voiced", 0.19, ee, 103.0, 0.9),
        ("silence", 0.07, None, 102.0, 0.0),
        ("voiced", 0.14, eh, 102.0, 0.8),
        ("voiced", 0.12, liquid, 102.0, 0.68),
        ("silence", 0.07, None, 101.0, 0.0),
        ("voiced", 0.11, ah, 101.0, 0.82),
        ("voiced", 0.18, ee, 101.0, 0.88),
        ("silence", 0.97, None, 101.0, 0.0),
    )
    phrases = {
        ROBOT_SIGNATURE_TEXT: signature,
        ROBOT_GREETING_TEXT: greeting,
    }
    try:
        return phrases[text]
    except KeyError as exc:
        raise ValueError(f"unsupported robot phrase: {text}") from exc


def _render_robot_voiced(
    length: int,
    offset: int,
    *,
    f0: float,
    formants: Sequence[tuple[float, float, float]],
    level: float,
) -> array[float]:
    harmonics: list[tuple[float, float]] = []
    for harmonic in range(1, 48):
        frequency = f0 * harmonic
        if frequency >= SAMPLE_RATE / 2:
            break
        resonance = sum(
            gain * math.exp(-0.5 * ((frequency - center) / bandwidth) ** 2)
            for center, bandwidth, gain in formants
        )
        amplitude = (0.012 + resonance) / harmonic
        harmonics.append((frequency, amplitude))
    amplitude_sum = sum(amplitude for _, amplitude in harmonics) or 1.0
    attack = max(1, min(round(0.018 * SAMPLE_RATE), length // 4))
    release = max(1, min(round(0.025 * SAMPLE_RATE), length // 3))
    samples = array("f")
    for index in range(length):
        envelope = min(1.0, index / attack, (length - index - 1) / release)
        absolute_time = (offset + index) / SAMPLE_RATE
        value = sum(
            amplitude * math.sin(2.0 * math.pi * frequency * absolute_time)
            for frequency, amplitude in harmonics
        )
        samples.append(level * envelope * value / amplitude_sum)
    return samples


def _render_robot_noise(
    length: int,
    *,
    kind: str,
    level: float,
    generator: random.Random,
) -> array[float]:
    attack = max(1, min(round(0.008 * SAMPLE_RATE), length // 3))
    release = max(1, min(round(0.018 * SAMPLE_RATE), length // 3))
    previous = 0.0
    samples = array("f")
    for index in range(length):
        raw = generator.uniform(-1.0, 1.0)
        high = raw - previous * (0.72 if kind == "fricative" else 0.35)
        previous = raw
        envelope = min(1.0, index / attack, (length - index - 1) / release)
        if kind == "burst":
            envelope *= math.exp(-4.0 * index / max(1, length))
        samples.append(level * envelope * high)
    return samples


def _build_stereo_space(
    send_left: array[float],
    send_right: array[float],
    *,
    beat_length: float,
) -> tuple[array[float], array[float]]:
    left = array("f", [0.0]) * len(send_left)
    right = array("f", [0.0]) * len(send_right)

    # A very slow, shallow modulated delay widens sustained material without
    # detuning the dry melody enough to sound like a conventional chorus.
    chorus_base = round(0.024 * SAMPLE_RATE)
    chorus_depth = round(0.004 * SAMPLE_RATE)
    chorus_start = chorus_base + chorus_depth
    for index in range(chorus_start, len(left)):
        phase = 2.0 * math.pi * 0.17 * index / SAMPLE_RATE
        left_delay = chorus_base + round(chorus_depth * math.sin(phase))
        right_delay = chorus_base + round(
            chorus_depth * math.sin(phase + math.pi)
        )
        left[index] += 0.11 * send_left[index - left_delay]
        right[index] += 0.11 * send_right[index - right_delay]

    # A small cross-channel room reflection establishes depth before the two
    # filtered musical taps answer at the 3+2+3 accent points.
    room_delay = round(0.19 * SAMPLE_RATE)
    for index in range(room_delay, len(left)):
        left[index] += 0.045 * send_right[index - room_delay]
        right[index] += 0.045 * send_left[index - room_delay]

    def add_filtered_tap(delay_beats: float, gain: float, cross: float) -> None:
        delay = max(1, round(delay_beats * beat_length * SAMPLE_RATE))
        filtered_left = 0.0
        filtered_right = 0.0
        for index in range(delay, len(left)):
            source = index - delay
            filtered_left = 0.86 * filtered_left + 0.14 * send_left[source]
            filtered_right = 0.86 * filtered_right + 0.14 * send_right[source]
            left[index] += gain * (
                (1.0 - cross) * filtered_left + cross * filtered_right
            )
            right[index] += gain * (
                (1.0 - cross) * filtered_right + cross * filtered_left
            )

    add_filtered_tap(1.5, 0.16, 0.68)
    add_filtered_tap(2.5, 0.085, 0.82)
    return left, right


def _mix_tone(
    samples: array[float],
    tone: _Tone,
    *,
    gain: float = 1.0,
    secondary_samples: array[float] | None = None,
    secondary_gain: float = 0.0,
) -> None:
    start = max(0, round(tone.start * SAMPLE_RATE))
    length = max(1, round(tone.duration * SAMPLE_RATE))
    end = min(len(samples), start + length)
    frequency = 440.0 * 2.0 ** ((tone.note - 69.0) / 12.0)
    if tone.voice == "piano":
        attack = min(0.012, tone.duration * 0.1)
        release = min(0.55, tone.duration * 0.55)
    elif tone.voice in {"strings", "cello"}:
        attack = min(0.38, tone.duration * 0.28)
        release = min(0.7, tone.duration * 0.35)
    else:
        attack = min(0.035, tone.duration * 0.2)
        release = min(0.25, tone.duration * 0.4)
    for index in range(start, end):
        elapsed = (index - start) / SAMPLE_RATE
        remaining = tone.duration - elapsed
        envelope = min(
            1.0,
            elapsed / max(attack, 1 / SAMPLE_RATE),
            remaining / max(release, 1 / SAMPLE_RATE),
        )
        phase = 2.0 * math.pi * frequency * elapsed
        if tone.voice == "bell":
            value = (
                math.sin(phase)
                + 0.32 * math.sin(phase * 2.01)
                + 0.14 * math.sin(phase * 3.97)
            )
            envelope *= math.exp(-2.8 * elapsed / tone.duration)
        elif tone.voice == "piano":
            value = (
                math.sin(phase)
                + 0.42 * math.sin(phase * 2.0 + 0.12)
                + 0.2 * math.sin(phase * 3.01)
                + 0.08 * math.sin(phase * 5.02)
            )
            envelope *= math.exp(-1.5 * elapsed / tone.duration)
        elif tone.voice == "strings":
            shaped_phase = phase + 0.28 * math.sin(2.0 * math.pi * 5.1 * elapsed)
            value = (
                math.sin(shaped_phase)
                + 0.31 * math.sin(shaped_phase * 2.0)
                + 0.15 * math.sin(shaped_phase * 3.0)
                + 0.07 * math.sin(shaped_phase * 4.0)
            )
        elif tone.voice == "cello":
            shaped_phase = phase + 0.17 * math.sin(2.0 * math.pi * 4.6 * elapsed)
            value = (
                math.sin(shaped_phase)
                + 0.25 * math.sin(shaped_phase * 2.0)
                + 0.09 * math.sin(shaped_phase * 3.0)
            )
        elif tone.voice == "dark":
            value = math.sin(phase) + 0.18 * math.sin(phase * 0.5)
        else:
            value = math.sin(phase) + 0.2 * math.sin(phase * 2.0)
        sample = tone.volume * envelope * value
        samples[index] += gain * sample
        if secondary_samples is not None:
            secondary_samples[index] += secondary_gain * sample


def _mix_noise(
    samples: array[float],
    noise: _Noise,
    *,
    gain: float = 1.0,
    secondary_samples: array[float] | None = None,
    secondary_gain: float = 0.0,
) -> None:
    start = max(0, round(noise.start * SAMPLE_RATE))
    length = max(1, round(noise.duration * SAMPLE_RATE))
    end = min(len(samples), start + length)
    generator = random.Random(noise.seed)
    smooth = 0.0
    for index in range(start, end):
        elapsed = (index - start) / SAMPLE_RATE
        remaining = noise.duration - elapsed
        envelope = min(1.0, elapsed / 0.08, remaining / 0.3)
        raw = generator.uniform(-1.0, 1.0)
        smooth = smooth * 0.94 + raw * 0.06
        sample = noise.volume * envelope * (raw * 0.25 + smooth)
        samples[index] += gain * sample
        if secondary_samples is not None:
            secondary_samples[index] += secondary_gain * sample


def _spawn(
    player: Sequence[str],
    path: Path,
    *,
    popen: Callable[..., subprocess.Popen[bytes]],
) -> subprocess.Popen[bytes]:
    return popen(
        [*player, str(path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=0.25)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=0.25)


def _normalized_slot(slot: int | None) -> int | None:
    if slot is None:
        return None
    if not 0 <= slot < len(SESSION_INTERVALS):
        raise ValueError("audio session slot must be between 0 and 7")
    return slot
