from __future__ import annotations

import io
from unittest import TestCase
from unittest.mock import patch

from pad_lattice.devices.base import ExperienceView, ShowColor, SurfaceView
from pad_lattice.show import (
    OFF,
    SHOW_ACTS,
    SHOW_HEIGHT,
    SHOW_TOKENS,
    SHOW_WIDTH,
    build_constellation_show,
    run_show_surface,
    show_duration,
)


class FakeShowSurface:
    profile_id = "test/grid/device"
    surface_kind = "midi"
    input_name = "input"
    output_name = "output"
    selector_capacity = 8
    accent_names = ("cyan", "magenta", "lime", "orange", "violet", "teal", "rose", "sky")
    visual_protocol = 1

    def __init__(self, *, fail_initialize: bool = False) -> None:
        self.fail_initialize = fail_initialize
        self.initialized = False
        self.closed = False
        self.frames = []
        self.experiences = []

    def initialize(self) -> None:
        self.initialized = True
        if self.fail_initialize:
            raise OSError("initialization failed")

    def render_show_frame(self, frame) -> None:
        self.frames.append(frame)

    def render(self, view: SurfaceView) -> None:
        raise AssertionError("Show rendered a semantic frame")

    def set_experience(self, view: ExperienceView) -> None:
        self.experiences.append(view)

    def poll_events(self):
        return []

    def close(self) -> None:
        self.closed = True


class FakeSoundtrack:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class StepClock:
    def __init__(self, step: float = 1.0) -> None:
        self.value = -step
        self.step = step

    def __call__(self) -> float:
        self.value += self.step
        return self.value


class ShowTest(TestCase):
    def test_reference_show_is_a_complete_eight_act_story(self) -> None:
        cues = build_constellation_show()

        self.assertEqual(len(cues), 80)
        self.assertEqual(tuple(dict.fromkeys(cue.act for cue in cues)), SHOW_ACTS)
        self.assertAlmostEqual(show_duration(cues), 43.1)
        self.assertGreaterEqual(min(cue.duration for cue in cues), 0.22)
        self.assertEqual(cues[0].act, "Prelude - Alone")
        self.assertEqual(cues[-1].act, "Finale - A Constellation")
        self.assertEqual(
            tuple(cue.caption for cue in cues if cue.caption is not None),
            (
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
            ),
        )

    def test_every_frame_has_rgb_and_palette_fallback(self) -> None:
        rgb_values = set()
        for cue in build_constellation_show():
            with self.subTest(act=cue.act):
                self.assertEqual(len(cue.frame.grid), SHOW_HEIGHT)
                self.assertTrue(
                    all(len(row) == SHOW_WIDTH for row in cue.frame.grid)
                )
                self.assertEqual(len(cue.frame.top), SHOW_WIDTH)
                self.assertEqual(len(cue.frame.right), SHOW_HEIGHT)
                colors = {
                    *cue.frame.top,
                    *cue.frame.right,
                    *(color for row in cue.frame.grid for color in row),
                }
                self.assertTrue(all(isinstance(color, ShowColor) for color in colors))
                self.assertLessEqual(
                    {color.fallback for color in colors},
                    SHOW_TOKENS,
                )
                rgb_values.update(color.rgb for color in colors)
        self.assertGreater(len(rgb_values), 80)

    def test_story_avoids_full_surface_on_off_strobing(self) -> None:
        frames = [
            tuple(
                [color.fallback for row in cue.frame.grid for color in row]
                + [color.fallback for color in cue.frame.top]
                + [color.fallback for color in cue.frame.right]
            )
            for cue in build_constellation_show()
        ]

        for previous, current in zip(frames, frames[1:]):
            switched = sum(
                (before == OFF) != (after == OFF)
                for before, after in zip(previous, current)
            )
            self.assertLessEqual(switched, 40)

    def test_runner_uses_absolute_timing_and_closes(self) -> None:
        surface = FakeShowSurface()
        output = io.StringIO()

        completed = run_show_surface(
            surface,
            tempo=2.0,
            output=output,
            clock=StepClock(0.5),
            sleep=lambda _: None,
        )

        self.assertTrue(completed)
        self.assertTrue(surface.initialized)
        self.assertTrue(surface.closed)
        self.assertGreater(len(surface.frames), 20)
        self.assertLessEqual(len(surface.frames), len(build_constellation_show()))
        self.assertEqual(surface.experiences[0].status, "starting")
        self.assertEqual(surface.experiences[-1].status, "idle")
        self.assertIn("A Spark Becomes a Constellation", output.getvalue())

    def test_runner_synchronizes_and_closes_optional_soundtrack(self) -> None:
        surface = FakeShowSurface()
        soundtrack = FakeSoundtrack()
        timelines = []
        with patch(
            "pad_lattice.experience_runtime.start_constellation_soundtrack",
            side_effect=lambda timeline: (
                timelines.append(tuple(timeline)) or soundtrack
            ),
        ):
            completed = run_show_surface(
                surface,
                tempo=2.0,
                audio=True,
                output=io.StringIO(),
                clock=StepClock(1.0),
                sleep=lambda _: None,
            )

        self.assertTrue(completed)
        self.assertTrue(soundtrack.closed)
        self.assertEqual(len(timelines), 1)
        self.assertEqual(timelines[0][0].start, 0.0)
        cues = build_constellation_show()
        self.assertEqual(timelines[0][0].duration, cues[0].duration / 2)
        self.assertAlmostEqual(
            timelines[0][-1].start + timelines[0][-1].duration,
            show_duration(cues, tempo=2.0),
        )

    def test_runner_restores_surface_after_interrupt(self) -> None:
        surface = FakeShowSurface()
        completed = run_show_surface(
            surface,
            output=io.StringIO(),
            clock=StepClock(),
            sleep=lambda _: (_ for _ in ()).throw(KeyboardInterrupt()),
        )

        self.assertFalse(completed)
        self.assertTrue(surface.closed)

    def test_initialization_failure_still_closes_surface(self) -> None:
        surface = FakeShowSurface(fail_initialize=True)

        with self.assertRaisesRegex(OSError, "initialization failed"):
            run_show_surface(surface, output=io.StringIO())

        self.assertTrue(surface.closed)

    def test_soundtrack_failure_still_closes_surface(self) -> None:
        surface = FakeShowSurface()

        with patch(
            "pad_lattice.experience_runtime.start_constellation_soundtrack",
            side_effect=ValueError("audio failed"),
        ):
            with self.assertRaisesRegex(ValueError, "audio failed"):
                run_show_surface(
                    surface,
                    audio=True,
                    output=io.StringIO(),
                    clock=StepClock(),
                    sleep=lambda _: None,
                )

        self.assertTrue(surface.closed)
