from pathlib import Path
from tempfile import TemporaryDirectory
import threading
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from pad_lattice.desktop_service import DesktopSurface
from pad_lattice.devices.base import ExperienceView, SessionIndicator, SurfaceView
from pad_lattice.devices.profiles import ProfileCatalog
from pad_lattice.events import AgentState
from test_profile_testing import FakeSurface


class DesktopHardwareTest(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.bridge = DesktopSurface(Path(directory.name), str(Path(directory.name) / "test.sock"),
                                     lambda _: None, threading.Event())
        self.addCleanup(self.bridge.close)
        self.hardware = FakeSurface()
        self.hardware.events = []
        profile = ProfileCatalog.load(include_user=False).get(self.hardware.profile_id)
        for target, value in (("list_midi_ports", ([self.hardware.input_name], [self.hardware.output_name])),
                              ("resolve_device", SimpleNamespace(profile=profile)),
                              ("open_resolved_surface", self.hardware)):
            patcher = patch(f"pad_lattice.desktop_service.{target}", return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.params = dict(profile=profile.id, input=self.hardware.input_name,
                           output=self.hardware.output_name, confirmed=True)

    def start(self):
        return self.bridge.command("profile_test_start", self.params)

    def test_requires_explicit_ports_confirmation_and_exclusive_access(self):
        for params in ({}, {**self.params, "confirmed": False}, {**self.params, "input": "missing"}):
            with self.assertRaises(ValueError):
                self.bridge.command("profile_test_start", params)
        self.bridge.midi = self.hardware
        with self.assertRaisesRegex(ValueError, "Disconnect.*MIDI"):
            self.start()
        self.bridge.midi = None
        self.bridge.last_experience = ExperienceView("playing", "show")
        with self.assertRaisesRegex(ValueError, "Show"):
            self.start()
        self.bridge.last_experience = ExperienceView("idle")
        self.bridge.last_view = SurfaceView(AgentState.RUNNING, sessions=(SessionIndicator(0, AgentState.RUNNING),))
        with self.assertRaisesRegex(ValueError, "Codex"):
            self.start()
        self.bridge.last_view = SurfaceView(None)
        self.bridge.tool_pending = True
        with self.assertRaises(ValueError):
            self.start()

    def test_step_scoping_input_isolation_and_cancelled_report(self):
        from pad_lattice.devices.base import ActionPressed
        from pad_lattice.events import ControlAction
        result = self.start()
        with self.assertRaises(ValueError):
            self.bridge.command("connect_midi", self.params)
        self.hardware.events = [ActionPressed(ControlAction.APPROVE)]
        self.assertEqual(self.bridge.poll_events(), [])
        with self.assertRaises(ValueError):
            self.bridge.command("profile_test_answer", {"run_id": "old", "step_id": "visual:idle", "passed": True})
        with self.assertRaises(ValueError):
            self.bridge.command("profile_test_report", {"run_id": result["run_id"]})
        self.bridge.command("profile_test_cancel", {"run_id": result["run_id"]})
        report = self.bridge.command("profile_test_report", {"run_id": result["run_id"]})
        self.assertFalse(report["passed"])
        self.assertEqual(report["results"]["failure_stage"], "cancelled")
        self.assertTrue(self.hardware.closed)

    def test_new_session_and_playback_cancel_test(self):
        self.start()
        self.bridge.render(SurfaceView(AgentState.RUNNING, sessions=(SessionIndicator(0, AgentState.RUNNING),)))
        self.assertEqual(self.bridge.profile_test.failure_stage, "live_session")
        self.assertTrue(self.hardware.closed)
        self.bridge.last_view = SurfaceView(None)
        self.start()
        self.bridge.set_experience(ExperienceView("starting", "demo"))
        self.assertEqual(self.bridge.profile_test.failure_stage, "playback")

    def test_absent_interface_cancels_test_and_attach_cannot_run(self):
        messages = []
        self.bridge.emit = messages.append
        self.start()
        self.bridge.requests.put({"id": 1, "method": "attach_conversation", "params": {"thread_id": "x"}})
        self.bridge.poll_events()
        self.assertIn("Stop the hardware test", messages[-1]["error"])
        self.bridge.profile_test_seen -= 31
        self.bridge.poll_events()
        self.assertEqual(self.bridge.profile_test.failure_stage, "interface_timeout")
        self.assertTrue(self.hardware.closed)

    def test_attention_is_ordered_without_private_session_metadata(self):
        sessions = [{"slot": slot, "label": label, "accent": "cyan", "state": state,
                     "selected": slot == 0, "state_age_seconds": age,
                     "session_id": "private-id", "metadata": {"cwd": "/private/path"}}
                    for slot, label, state, age in (
                        (0, "Reply", "waiting_for_reply", 30), (1, "New approval", "waiting_for_approval", 5),
                        (2, "Old approval", "waiting_for_approval", 90), (3, "Working", "running", 100),
                        (None, "Overflow", "waiting_for_approval", 120), (4, "Error", "error", 1))]
        with patch("pad_lattice.desktop_service.PadLatticeClient") as client:
            client.return_value.status.return_value = {"sessions": sessions, "control_revision": 42, "overflow_count": 1}
            result = self.bridge.attention()
        self.assertEqual([item["slot"] for item in result["sessions"]], [2, 1, 4, 0])
        self.assertEqual(result["revision"], 42)
        self.assertNotIn("private", str(result))

    def test_removed_ports_cancel_even_if_driver_does_not_report_an_error(self):
        self.start()
        self.bridge.profile_test_ports_checked -= 3
        with patch("pad_lattice.desktop_service.list_midi_ports", return_value=([], [])):
            self.bridge.poll_events()
        self.assertEqual(self.bridge.profile_test.failure_stage, "disconnected")
        self.assertTrue(self.hardware.closed)
