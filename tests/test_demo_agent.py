from __future__ import annotations

import io
from unittest import TestCase

from pad_lattice.demo_agent import run_demo_surface
from pad_lattice.devices.base import ActionPressed, SessionSelected
from pad_lattice.events import AgentState, ControlAction


class FakeSurface:
    profile_id = "test/grid/device"
    surface_kind = "midi"
    input_name = "input"
    output_name = "output"
    selector_capacity = 8
    accent_names = ("cyan", "magenta", "lime", "orange", "violet", "teal", "rose", "sky")
    visual_protocol = 1

    def __init__(self, polls=()) -> None:
        self.polls = list(polls)
        self.views = []
        self.experiences = []
        self.initialized = False
        self.closed = False

    def initialize(self) -> None:
        self.initialized = True

    def render(self, view) -> None:
        self.views.append(view)

    def render_show_frame(self, frame) -> None:
        raise AssertionError("Demo rendered a Show frame")

    def set_experience(self, view) -> None:
        self.experiences.append(view)

    def poll_events(self):
        return self.polls.pop(0) if self.polls else []

    def close(self) -> None:
        self.closed = True


class FailingSurface(FakeSurface):
    def initialize(self) -> None:
        raise OSError("initialization failed")


class FakeAudioFeedback:
    def __init__(self) -> None:
        self.calls = []
        self.closed = False

    def play(self, cue, *, slot=None) -> None:
        self.calls.append((cue, slot))

    def close(self) -> None:
        self.closed = True


class IncrementingClock:
    def __init__(self) -> None:
        self.value = -1.0

    def __call__(self) -> float:
        self.value += 1.0
        return self.value


class DemoAgentTest(TestCase):
    def test_shared_multi_agent_demo_accepts_scene_and_action_input(self) -> None:
        surface = FakeSurface(
            (
                [SessionSelected(1)],
                [ActionPressed(ControlAction.APPROVE)],
                [SessionSelected(2)],
                [ActionPressed(ControlAction.RETRY)],
            )
        )
        output = io.StringIO()
        audio_feedback = FakeAudioFeedback()

        actions = run_demo_surface(
            surface,
            poll_interval=0,
            output=output,
            audio_feedback=audio_feedback,
            clock=IncrementingClock(),
            sleep=lambda _: None,
        )

        self.assertEqual(actions, (ControlAction.APPROVE, ControlAction.RETRY))
        self.assertTrue(surface.initialized)
        self.assertTrue(surface.closed)
        self.assertEqual(len(surface.views), 5)
        self.assertEqual(surface.views[0].sessions[0].label, "Builder")
        self.assertEqual(surface.views[1].selected_state, AgentState.WAITING_FOR_APPROVAL)
        self.assertEqual(surface.views[-1].selected_state, AgentState.SUCCESS)
        self.assertEqual(surface.experiences[0].kind, "demo")
        self.assertEqual(surface.experiences[-1].status, "idle")
        self.assertIn("The Reviewer needs you.", output.getvalue())
        self.assertIn("The agents form a constellation.", output.getvalue())
        self.assertTrue(audio_feedback.calls)
        self.assertTrue(audio_feedback.closed)

    def test_initialization_failure_still_closes_surface(self) -> None:
        surface = FailingSurface()

        with self.assertRaisesRegex(OSError, "initialization failed"):
            run_demo_surface(surface, sleep=lambda _: None)

        self.assertTrue(surface.closed)
