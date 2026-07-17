from __future__ import annotations

import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from pad_lattice.devices.base import ActionPressed, SessionSelected
from pad_lattice.devices.profiles import ProfileCatalog
from pad_lattice.devices.testing import run_profile_test
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
    visual_protocol = "0.1"

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
        self.assertEqual(len(surface.views), 18)
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
