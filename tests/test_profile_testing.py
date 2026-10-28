from __future__ import annotations

import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from pad_lattice.devices.base import ActionPressed, SessionSelected
from pad_lattice.devices.profiles import ProfileCatalog
from pad_lattice.devices.testing import run_profile_test
from pad_lattice.devices.test_run import ProfileTestRun
from pad_lattice.events import ControlAction


class FakeSurface:
    profile_id = "novation/launchpad/pro-mk1"
    input_name = "Launchpad test input"
    output_name = "Launchpad test output"
    selector_capacity = 8
    accent_names = (
        "cyan",
        "magenta",
        "lime",
        "orange",
        "violet",
        "teal",
        "rose",
        "sky",
    )
    visual_protocol = 1

    def __init__(self, *, fail_initialize: bool = False) -> None:
        self.fail_initialize = fail_initialize
        self.events = [
            *(ActionPressed(action) for action in ControlAction),
            *(SessionSelected(slot) for slot in range(self.selector_capacity)),
        ]
        self.views = []
        self.closed = False

    def initialize(self) -> None:
        if self.fail_initialize:
            raise RuntimeError("private/path/that/must/not/be/reported")

    def render(self, view) -> None:
        self.views.append(view)

    def poll_events(self):
        return [self.events.pop(0)] if self.events else []

    def close(self) -> None:
        self.closed = True


class ProfileTestingTest(TestCase):
    def setUp(self) -> None:
        self.profile = ProfileCatalog.load(include_user=False).get(
            "novation/launchpad/pro-mk1"
        )

    def test_complete_run_writes_passing_sanitized_report(self) -> None:
        surface = FakeSurface()
        answers = io.StringIO("yes\n" * 9)
        output = io.StringIO()

        with TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.json"
            report = run_profile_test(
                surface,
                self.profile,
                report_path,
                input_stream=answers,
                output_stream=output,
                event_timeout=0.1,
                settle_delay=0.0,
            )
            saved = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertTrue(report["passed"])
        self.assertEqual(saved, report)
        self.assertTrue(surface.closed)
        self.assertEqual(len(surface.views), 21)
        serialized = json.dumps(report)
        self.assertNotIn("prompt", serialized.lower())
        self.assertNotIn("session_id", serialized)

    def test_initialize_failure_still_closes_and_writes_sanitized_report(self) -> None:
        surface = FakeSurface(fail_initialize=True)

        with TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.json"
            with self.assertRaisesRegex(RuntimeError, "private/path"):
                run_profile_test(
                    surface,
                    self.profile,
                    report_path,
                    input_stream=io.StringIO(),
                    output_stream=io.StringIO(),
                    settle_delay=0.0,
                )
            saved = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertTrue(surface.closed)
        self.assertFalse(saved["passed"])
        self.assertEqual(saved["results"]["failure_stage"], "initialize")
        self.assertNotIn("private/path", json.dumps(saved))

    def test_answers_are_step_scoped_and_inputs_require_hardware(self):
        surface = FakeSurface()
        run = ProfileTestRun(surface, self.profile)
        run.start()
        run.answer("visual:idle", True)
        with self.assertRaisesRegex(ValueError, "another step"):
            run.answer("visual:idle", True)
        while run.step.group == "visual":
            run.answer(run.step.id, True)
        with self.assertRaisesRegex(ValueError, "controller"):
            run.answer(run.step.id, True)
        surface.events = [ActionPressed(ControlAction.REJECT)]
        run.tick()
        self.assertEqual(run.step.key, "approve")
        surface.events = [ActionPressed(ControlAction.APPROVE)]
        run.tick()
        self.assertTrue(run.checks["actions"]["approve"])
        run.cancel()
        self.assertTrue(surface.closed)
        self.assertEqual(run.status, "cancelled")

    def test_input_timeout_and_driver_failure_are_reported(self):
        from unittest.mock import patch
        now = [100.0]
        surface = FakeSurface()
        surface.events = []
        run = ProfileTestRun(surface, self.profile, clock=lambda: now[0])
        run.start()
        while run.step.group == "visual":
            run.answer(run.step.id, True)
        now[0] += 16
        run.tick()
        self.assertFalse(run.checks["actions"]["approve"])
        self.assertEqual(run.step.key, "reject")
        with patch.object(surface, "poll_events", side_effect=OSError("private driver detail")):
            run.tick()
        self.assertEqual(run.failure_stage, "input")
        self.assertTrue(surface.closed)
        self.assertNotIn("private", json.dumps(run.snapshot()))

    def test_one_input_batch_cannot_advance_multiple_steps(self):
        from unittest.mock import patch
        run = ProfileTestRun(FakeSurface(), self.profile)
        run.start()
        while run.step.group == "visual":
            run.answer(run.step.id, True)
        with patch.object(run.surface, "poll_events", return_value=[ActionPressed(action) for action in ControlAction]):
            run.tick()
        self.assertEqual(run.step.key, "reject")
        run.cancel()
