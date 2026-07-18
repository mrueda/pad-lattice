from __future__ import annotations

import io
from unittest import TestCase

from pad_lattice.demo_agent import ANSWER_ACTIONS, DEMO_QUESTIONS, run_demo_surface
from pad_lattice.devices.base import ActionPressed
from pad_lattice.events import AgentState, ControlAction


class FakeSurface:
    profile_id = "test/grid/device"
    input_name = "input"
    output_name = "output"
    selector_capacity = 4
    accent_names = ("cyan",)
    visual_protocol = 1

    def __init__(self, polls=()) -> None:
        self.polls = list(polls)
        self.views = []
        self.initialized = False
        self.closed = False

    def initialize(self) -> None:
        self.initialized = True

    def render(self, view) -> None:
        self.views.append(view)

    def poll_events(self):
        if not self.polls:
            raise AssertionError("demo polled after the scripted input ended")
        return self.polls.pop(0)

    def close(self) -> None:
        self.closed = True


class FailingSurface(FakeSurface):
    def initialize(self) -> None:
        raise OSError("initialization failed")


class DemoAgentTest(TestCase):
    def test_guided_demo_asks_questions_and_renders_feedback(self) -> None:
        surface = FakeSurface(
            (
                [ActionPressed(ControlAction.STOP)],
                [ActionPressed(ControlAction.APPROVE)],
                [ActionPressed(ControlAction.REJECT)],
                [ActionPressed(ControlAction.APPROVE)],
            )
        )
        output = io.StringIO()

        answers = run_demo_surface(
            surface,
            poll_interval=0,
            feedback_seconds=0,
            success_seconds=0,
            output=output,
            sleep=lambda _: None,
        )

        self.assertEqual(
            answers,
            (
                ControlAction.APPROVE,
                ControlAction.REJECT,
                ControlAction.APPROVE,
            ),
        )
        self.assertTrue(surface.initialized)
        self.assertTrue(surface.closed)
        self.assertEqual(
            [view.selected_state for view in surface.views],
            [
                AgentState.WAITING_FOR_REPLY,
                AgentState.RUNNING,
                AgentState.WAITING_FOR_APPROVAL,
                AgentState.CANCELLED,
                AgentState.WAITING_FOR_REPLY,
                AgentState.RUNNING,
                AgentState.SUCCESS,
            ],
        )
        self.assertEqual(surface.views[0].available_actions, ANSWER_ACTIONS)
        self.assertEqual(surface.views[2].available_actions, ANSWER_ACTIONS)
        self.assertEqual(surface.views[4].available_actions, ANSWER_ACTIONS)
        self.assertIn(DEMO_QUESTIONS[0].prompt, output.getvalue())
        self.assertIn("Answer: yes", output.getvalue())
        self.assertIn("Answer: no", output.getvalue())
        self.assertIn("Demo complete.", output.getvalue())

    def test_initialization_failure_still_closes_surface(self) -> None:
        surface = FailingSurface()

        with self.assertRaisesRegex(OSError, "initialization failed"):
            run_demo_surface(surface, sleep=lambda _: None)

        self.assertTrue(surface.closed)
