from __future__ import annotations

import wave
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from pad_lattice.audio import (
    B_FLAT_MINOR_PITCH_CLASSES,
    EARCON_DESCRIPTIONS,
    REFERENCE_SCORE_MAX_ONSETS,
    REFERENCE_SCORE_MAX_POLYPHONY,
    REFERENCE_SCORE_MIN_PIANO_SPACE,
    REFERENCE_SCORE_STRING_CHORDS,
    ROBOT_GREETING_TEXT,
    ROBOT_SIGNATURE_TEXT,
    SAMPLE_RATE,
    AudioUnavailableError,
    Earcon,
    StoryBeat,
    SystemAudioFeedback,
    _constellation_score,
    _render_robot_phrase,
    _write_earcon,
    find_audio_player,
    start_constellation_soundtrack,
)
from pad_lattice.show import _story_timeline, build_constellation_show


class FakeProcess:
    def __init__(self) -> None:
        self.running = True
        self.terminated = False
        self.killed = False

    def poll(self):
        return None if self.running else 0

    def terminate(self) -> None:
        self.terminated = True
        self.running = False

    def kill(self) -> None:
        self.killed = True
        self.running = False

    def wait(self, timeout=None) -> int:
        self.running = False
        return 0


class FakePopen:
    def __init__(self) -> None:
        self.calls = []
        self.processes = []

    def __call__(self, command, **kwargs):
        process = FakeProcess()
        self.calls.append((command, kwargs))
        self.processes.append(process)
        return process


class AudioTest(TestCase):
    def test_every_earcon_has_a_description(self) -> None:
        self.assertEqual(set(EARCON_DESCRIPTIONS), set(Earcon))

    def test_earcon_renderer_writes_standard_mono_wav(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "success.wav"

            _write_earcon(path, Earcon.SUCCESS, 2)

            with wave.open(str(path), "rb") as source:
                self.assertEqual(source.getnchannels(), 1)
                self.assertEqual(source.getsampwidth(), 2)
                self.assertEqual(source.getframerate(), SAMPLE_RATE)
                self.assertGreater(source.getnframes(), 0)

    def test_system_feedback_caches_debounces_and_cleans_up(self) -> None:
        popen = FakePopen()
        times = iter((1.0, 1.05, 2.0))
        feedback = SystemAudioFeedback(
            player=("fake-player",),
            popen=popen,
            clock=lambda: next(times),
        )
        directory = Path(feedback._directory.name)

        feedback.play(Earcon.APPROVE, slot=3)
        feedback.play(Earcon.APPROVE, slot=3)
        feedback.play(Earcon.APPROVE, slot=3)

        self.assertEqual(len(popen.calls), 2)
        self.assertEqual(popen.calls[0][0][0], "fake-player")
        self.assertEqual(popen.calls[0][0][-1], popen.calls[1][0][-1])
        self.assertTrue(Path(popen.calls[0][0][-1]).exists())

        feedback.close()

        self.assertFalse(directory.exists())
        self.assertTrue(all(process.terminated for process in popen.processes))

    def test_system_feedback_rejects_an_unknown_session_slot(self) -> None:
        feedback = SystemAudioFeedback(player=("fake-player",), popen=FakePopen())
        self.addCleanup(feedback.close)

        with self.assertRaisesRegex(ValueError, "between 0 and 7"):
            feedback.play(Earcon.SESSION_SELECTED, slot=8)

    def test_system_feedback_synthesizes_and_caches_robot_speech(self) -> None:
        popen = FakePopen()
        feedback = SystemAudioFeedback(
            player=("fake-player",),
            popen=popen,
            clock=lambda: 1.0,
        )
        self.addCleanup(feedback.close)

        feedback.speak(ROBOT_GREETING_TEXT)
        feedback.speak(ROBOT_GREETING_TEXT)

        self.assertEqual(len(popen.calls), 1)
        path = Path(popen.calls[0][0][-1])
        self.assertTrue(path.exists())
        with wave.open(str(path), "rb") as source:
            self.assertEqual(source.getnchannels(), 1)
            self.assertEqual(source.getframerate(), SAMPLE_RATE)
            self.assertEqual(source.getnframes(), round(10.32 * SAMPLE_RATE))

    def test_soundtrack_renders_eight_acts_and_removes_temporary_wav(self) -> None:
        timeline = tuple(
            StoryBeat(
                beat.act,
                beat.caption,
                beat.start * 0.04,
                beat.duration * 0.04,
            )
            for beat in _story_timeline(build_constellation_show(), tempo=1.0)
        )
        popen = FakePopen()

        soundtrack = start_constellation_soundtrack(
            timeline,
            player=("fake-player",),
            popen=popen,
        )
        path = Path(popen.calls[0][0][-1])

        self.assertTrue(path.exists())
        with wave.open(str(path), "rb") as source:
            self.assertEqual(source.getnchannels(), 2)
            self.assertEqual(source.getframerate(), SAMPLE_RATE)
        soundtrack.close()
        self.assertFalse(path.exists())

    def test_soundtrack_rejects_a_story_missing_named_cues(self) -> None:
        timeline = tuple(
            StoryBeat(f"act-{index}", None, index * 0.1, 0.1)
            for index in range(8)
        )

        with self.assertRaisesRegex(ValueError, "missing story cues"):
            start_constellation_soundtrack(
                timeline,
                player=("fake-player",),
                popen=FakePopen(),
            )

    def test_reference_score_is_sparse_consonant_and_stays_in_key(self) -> None:
        timeline = _story_timeline(build_constellation_show(), tempo=1.0)
        duration = max(beat.start + beat.duration for beat in timeline)
        tones, _, speeches = _constellation_score(timeline, duration)

        onsets = {round(tone.start, 6) for tone in tones}
        self.assertLessEqual(len(onsets), REFERENCE_SCORE_MAX_ONSETS)
        self.assertGreaterEqual(
            min(tone.space for tone in tones if tone.voice == "piano"),
            REFERENCE_SCORE_MIN_PIANO_SPACE,
        )
        string_tones = [tone for tone in tones if tone.voice == "strings"]
        string_onsets = {round(tone.start, 6) for tone in string_tones}
        self.assertEqual(len(string_onsets), REFERENCE_SCORE_STRING_CHORDS)
        self.assertTrue(
            all(
                sum(round(tone.start, 6) == onset for tone in string_tones) == 3
                for onset in string_onsets
            )
        )
        beat_length = (duration - timeline[0].start) / 64
        self.assertGreaterEqual(
            min(tone.duration for tone in string_tones),
            2 * beat_length - 1e-9,
        )
        pitch_classes = {round(tone.note) % 12 for tone in tones}
        self.assertLessEqual(pitch_classes, B_FLAT_MINOR_PITCH_CLASSES)

        events = []
        for tone in tones:
            events.extend(
                (
                    (tone.start, 1),
                    (tone.start + tone.duration, -1),
                )
            )
        active = 0
        maximum = 0
        for _, delta in sorted(events, key=lambda event: (event[0], event[1])):
            active += delta
            maximum = max(maximum, active)
        self.assertLessEqual(maximum, REFERENCE_SCORE_MAX_POLYPHONY)

        for index, left in enumerate(tones):
            for right in tones[index + 1 :]:
                overlap = min(
                    left.start + left.duration,
                    right.start + right.duration,
                ) - max(left.start, right.start)
                interval = abs(round(left.note) - round(right.note))
                if interval == 1:
                    self.assertLessEqual(overlap, 0.12)

        self.assertEqual(len(speeches), 1)
        signature = speeches[0]
        self.assertEqual(signature.text, ROBOT_SIGNATURE_TEXT)
        self.assertGreaterEqual(signature.start, next(
            beat.start for beat in timeline if beat.caption == "Pad-Lattice"
        ))
        self.assertLessEqual(signature.start + signature.duration, duration)

    def test_robot_signature_is_deterministic_formant_speech(self) -> None:
        first = _render_robot_phrase(ROBOT_SIGNATURE_TEXT, 1.6)
        second = _render_robot_phrase(ROBOT_SIGNATURE_TEXT, 1.6)
        greeting = _render_robot_phrase(ROBOT_GREETING_TEXT, 10.32)

        self.assertEqual(first, second)
        self.assertEqual(len(first), round(1.6 * SAMPLE_RATE))
        self.assertGreater(max(abs(sample) for sample in first), 0.99)
        self.assertEqual(len(greeting), round(10.32 * SAMPLE_RATE))
        self.assertGreater(max(abs(sample) for sample in greeting), 0.99)
        with self.assertRaisesRegex(ValueError, "unsupported robot phrase"):
            _render_robot_phrase("HELLO", 1.0)

    def test_player_detection_prefers_pipewire(self) -> None:
        with patch(
            "pad_lattice.audio.shutil.which",
            side_effect=lambda name: "/usr/bin/pw-play" if name == "pw-play" else None,
        ):
            self.assertEqual(find_audio_player(), ("/usr/bin/pw-play",))

    def test_player_detection_reports_missing_system_audio(self) -> None:
        with patch("pad_lattice.audio.shutil.which", return_value=None):
            with self.assertRaises(AudioUnavailableError):
                find_audio_player()
