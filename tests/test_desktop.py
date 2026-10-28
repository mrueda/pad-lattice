from __future__ import annotations

from concurrent.futures import Future
import io
import json
import os
from pathlib import Path
import queue
import shutil
import socket
import subprocess
import sys
import threading
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
from unittest.mock import patch

from pad_lattice import PadLatticeClient, AgentIdentity, AgentState, ControlAction
from pad_lattice.codex_hooks import run_codex_hook, codex_hook_config_overrides
from pad_lattice.desktop_service import DesktopSurface
from pad_lattice.desktop_tools import inspect_codex


class EngineHarness:
    def __init__(self, command: list[str], root: Path):
        self.socket = str(root / "agent.sock")
        self.messages: queue.Queue = queue.Queue()
        self.process = subprocess.Popen(command + ["service", "--settings-dir", str(root / "settings"),
                                                 "--socket", self.socket],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True)
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()
        ready = self.messages.get(timeout=15)
        if ready.get("event") != "ready":
            self.close()
            raise AssertionError(ready)
        self.counter = 0

    def _read(self):
        for line in self.process.stdout:
            self.messages.put(json.loads(line))

    def request(self, method, params=None):
        self.counter += 1
        self.process.stdin.write(json.dumps({"id": self.counter, "method": method, "params": params or {}}) + "\n")
        self.process.stdin.flush()
        while True:
            message = self.messages.get(timeout=15)
            if message.get("id") == self.counter:
                if "error" in message:
                    raise ValueError(message["error"])
                return message["result"]

    def close(self):
        if not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
            raise
        self.thread.join(timeout=2)
        self.process.stdout.close()
        self.process.stderr.close()


class DesktopServiceTest(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="pl-desktop-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.engine = EngineHarness([sys.executable, "-m", "pad_lattice.desktop_entry"], self.root)
        self.addCleanup(self.engine.close)

    def test_snapshot_and_eof_release_socket(self):
        result = self.engine.request("snapshot")
        self.assertTrue(result["messages"][0]["admin"])
        self.assertEqual(result["messages"][1]["type"], "surface")
        self.engine.close()
        self.assertFalse(Path(self.engine.socket).exists())
        self.assertEqual(self.engine.process.returncode, 0)

    def test_second_engine_does_not_replace_existing_daemon(self):
        with self.assertRaises(AssertionError):
            EngineHarness([sys.executable, "-m", "pad_lattice.desktop_entry"], self.root)
        PadLatticeClient(self.engine.socket).ping()
        self.assertEqual(self.engine.request("snapshot")["messages"][1]["type"], "surface")

    def test_desktop_routes_to_only_the_selected_agent(self):
        client = PadLatticeClient(self.engine.socket)
        first, second = AgentIdentity("codex", "first"), AgentIdentity("codex", "second")
        for agent in (first, second):
            client.report_state(AgentState.WAITING_FOR_APPROVAL, agent=agent, reply=True)
        with client.subscribe_actions(first, (ControlAction.APPROVE,), request_id="a", one_shot=True, timeout=0.2) as a, \
                client.subscribe_actions(second, (ControlAction.APPROVE,), request_id="b", one_shot=True, timeout=2) as b:
            client.ping()
            self.engine.request("surface", {"protocol": 1, "type": "select_session", "slot": 1})
            self.engine.request("surface", {"protocol": 1, "type": "action", "action": "approve"})
            self.assertEqual(b.receive().agent, second)
            with self.assertRaises(socket.timeout):
                a.receive()

    def test_no_arbitrary_desktop_methods_or_public_binding(self):
        with self.assertRaises(ValueError):
            self.engine.request("launch_session")
        with self.assertRaises(ValueError):
            self.engine.request("exec", {"command": "anything"})
        with self.assertRaises(ValueError):
            self.engine.request("lan", {"host": "0.0.0.0"})
        with self.assertRaises(ValueError):
            self.engine.request("surface", {"protocol": 1, "type": "launch_session"})

    def test_settings_persist_with_private_permissions(self):
        self.engine.request("settings", {"codex": "/some path/codex", "audio_enabled": True})
        settings = self.root / "settings/settings.json"
        self.assertEqual(json.loads(settings.read_text())["codex"], "/some path/codex")
        self.assertEqual(settings.stat().st_mode & 0o777, 0o600)
        self.engine.request("settings", {"pad_focused": True})
        values = self.engine.request("settings")
        self.assertEqual(values, {"codex": "/some path/codex", "audio_enabled": True, "pad_focused": True})
        for invalid in ({"audio_enabled": "yes"}, {"pad_focused": 1}, {"terminal": "xterm"}, {"token": "secret"}):
            with self.assertRaises(ValueError):
                self.engine.request("settings", invalid)
        self.assertEqual(self.engine.request("settings"), values)
        self.engine.close()
        self.engine = EngineHarness([sys.executable, "-m", "pad_lattice.desktop_entry"], self.root)
        self.addCleanup(self.engine.close)
        self.assertEqual(self.engine.request("settings"), values)

    def test_demo_works_without_codex_or_midi(self):
        self.engine.request("surface", {"protocol": 1, "type": "start_experience", "kind": "demo"})
        snapshot = self.engine.request("snapshot")
        self.assertEqual(snapshot["messages"][2]["kind"], "demo")
        self.engine.request("surface", {"protocol": 1, "type": "stop_experience"})

    def test_attention_reads_daemon_without_blocking_and_rejects_reused_slots(self):
        client = PadLatticeClient(self.engine.socket)
        first, second = AgentIdentity("codex", "attention-first"), AgentIdentity("codex", "attention-second")
        client.report_state(AgentState.WAITING_FOR_APPROVAL, agent=first, reply=True)
        snapshot = self.engine.request("attention")
        self.assertEqual(snapshot["sessions"][0]["state"], "waiting_for_approval")
        self.assertGreaterEqual(snapshot["sessions"][0]["age_seconds"], 0)
        client.report_state(AgentState.RUNNING, agent=second, reply=True)
        self.engine.request("surface", {"protocol": 1, "type": "select_session", "slot": 1,
                                        "expected_revision": snapshot["revision"]})
        self.assertEqual(client.status()["selected"]["session_id"], first.session_id)


class DesktopToolsTest(TestCase):
    def test_theme_preference_persists_and_rejects_non_boolean_values(self):
        with TemporaryDirectory() as directory:
            surface = DesktopSurface(Path(directory), "/tmp/pad.sock", lambda _: None, threading.Event())
            self.addCleanup(surface.close)
            surface.command("settings", {"light_theme": True})
            self.assertIs(surface.settings()["light_theme"], True)
            surface.command("settings", {"light_theme": False})
            self.assertIs(surface.settings()["light_theme"], False)
            with self.assertRaises(ValueError):
                surface.command("settings", {"light_theme": "light"})
    def test_shared_network_pairing_uses_host_address_and_fixed_port(self):
        from unittest.mock import Mock
        with TemporaryDirectory() as directory:
            surface = DesktopSurface(Path(directory), "/tmp/pad.sock", lambda _: None, threading.Event())
            self.addCleanup(surface.close)
            listener = Mock()
            with patch("pad_lattice.web_surface.serve", return_value=listener) as serve:
                surface.server.set_lan("10.211.55.4", port=8001, advertise_host="192.168.1.45")
                self.assertEqual(serve.call_args.args[1:3], ("10.211.55.4", 8001))
                surface.server.set_lan("10.211.55.4", port=8001, advertise_host="192.168.1.46")
                self.assertEqual(serve.call_count, 1)
            pairing = surface.create_pairing()
            self.assertTrue(pairing["pairing_url"].startswith("http://192.168.1.46:8001/#pair="))
            self.assertTrue(surface.server._host_is_allowed("192.168.1.46:8001"))
            self.assertFalse(surface.server._host_is_allowed("192.168.1.45:8001"))
            self.assertFalse(surface.server._host_is_allowed("192.168.1.46:9999"))
            self.assertFalse(surface.server._host_is_allowed("evil.example:8001"))
            surface.server.set_lan(None)
            self.assertFalse(surface.server._host_is_allowed("192.168.1.46:8001"))
            self.assertIsNone(surface.server.network_url)

    def test_shared_network_rejects_public_addresses_and_invalid_ports(self):
        with TemporaryDirectory() as directory:
            surface = DesktopSurface(Path(directory), "/tmp/pad.sock", lambda _: None, threading.Event())
            self.addCleanup(surface.close)
            for advertised in ("8.8.8.8", "127.0.0.1", "0.0.0.0", "example.com"):
                with self.assertRaises(ValueError):
                    surface.server.set_lan("10.211.55.4", port=8001, advertise_host=advertised)
            for port in (0, -1, 65536, True, "8001"):
                with self.assertRaises(ValueError):
                    surface.server.set_lan("10.211.55.4", port=port)

    def test_audio_reaches_desktop_and_browsers_without_snapshot_replay(self):
        messages = []
        with TemporaryDirectory() as directory:
            surface = DesktopSurface(Path(directory), "/tmp/pad.sock", messages.append, threading.Event())
            self.addCleanup(surface.close)
            with patch.object(surface.server, "broadcast_audio") as broadcast:
                surface.emit_audio("approval", 2)
            broadcast.assert_called_once_with("approval", 2)
            self.assertEqual(messages[-1]["payload"],
                {"protocol": 1, "type": "audio_cue", "cue": "approval", "slot": 2})
            self.assertNotIn("audio_cue", [item["type"] for item in surface.snapshot()["messages"]])

    def test_lan_reconfiguration_preserves_listener_on_bind_failure(self):
        from unittest.mock import Mock
        with TemporaryDirectory() as directory:
            surface = DesktopSurface(Path(directory), "/tmp/pad.sock", lambda _: None, threading.Event())
            self.addCleanup(surface.close)
            listener = Mock()
            with patch("pad_lattice.web_surface.serve", return_value=listener):
                surface.server.set_lan("192.168.1.10")
            with patch("pad_lattice.web_surface.serve", side_effect=OSError("address unavailable")):
                with self.assertRaises(OSError):
                    surface.server.set_lan("192.168.1.11")
            self.assertEqual(surface.server.host, "192.168.1.10")
            listener.shutdown.assert_not_called()
            surface.server.set_lan(None)
            listener.shutdown.assert_called_once()
            self.assertEqual(surface.server.host, "127.0.0.1")

    def test_session_end_cleans_up_identity(self):
        sent = []
        run_codex_hook("/tmp/test.sock", io.StringIO(json.dumps({
            "hook_event_name": "SessionEnd", "session_id": "closed-session"})), io.StringIO(),
            sender=lambda path, message: sent.append(message))
        self.assertEqual(sent[0]["type"], "session_end")
        self.assertEqual(sent[0]["agent"]["session_id"], "closed-session")

    def test_midi_failure_leaves_browser_surface_available(self):
        with TemporaryDirectory() as directory:
            surface = DesktopSurface(Path(directory), "/tmp/pad.sock", lambda _: None, threading.Event())
            from unittest.mock import Mock
            midi = Mock()
            midi.render.side_effect = OSError("device removed")
            surface.midi = midi
            surface._midi_call("render", surface.last_view)
            self.assertIsNone(surface.midi)
            self.assertEqual(surface.snapshot()["messages"][1]["type"], "surface")
            surface.close()

    @skipUnless(shutil.which("codex"), "Codex CLI not installed")
    def test_installed_codex_exposes_current_hooks(self):
        result = inspect_codex()
        self.assertTrue(result["available"], result)
        command = [str(result["path"])]
        for override in codex_hook_config_overrides("/bin/true"):
            command.extend(["-c", override])
        # Parse every hook definition through Codex itself, without starting a model turn.
        parsed = subprocess.run(command + ["features", "list"], capture_output=True, text=True, timeout=10)
        self.assertEqual(parsed.returncode, 0, parsed.stderr)


class DesktopOperationsTest(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="pl-operations-")
        self.addCleanup(self.temp.cleanup)
        self.messages = []
        self.surface = DesktopSurface(Path(self.temp.name), "/tmp/pad.sock",
                                      self.messages.append, threading.Event())
        self.addCleanup(self.surface.close)

    def request(self, request_id, method, **params):
        self.surface.requests.put_nowait({"id": request_id, "method": method, "params": params})
        self.surface.poll_events()

    def test_overlapping_inspections_share_result_and_allow_a_session_operation(self):
        inspection = Future()
        with patch.object(self.surface.workers, "submit", return_value=inspection) as submit, \
                patch.object(self.surface.attachments, "attach", return_value={"slot": 0}) as attach:
            self.request(1, "inspect_codex")
            self.request(2, "inspect_codex")
            submit.assert_called_once_with(inspect_codex, "")
            self.assertFalse(self.surface.tool_pending)
            self.request(3, "attach_conversation", thread_id="example")
            self.assertEqual(submit.call_count, 2)
            self.assertEqual(self.messages, [])
            inspection.set_result({"available": True, "version": "0.165.0"})
            submit.call_args.args[0]()
            attach.assert_called_once_with("example")
            self.assertEqual([message["id"] for message in self.messages], [1, 2, 3])
            self.assertTrue(all("result" in message for message in self.messages))
            self.assertEqual(self.messages[0]["result"], self.messages[1]["result"])
            self.assertFalse(self.surface.tool_pending)

    def test_changed_executable_is_checked_separately_and_failed_checks_can_retry(self):
        first, second, retry = Future(), Future(), Future()
        with patch.object(self.surface.workers, "submit", side_effect=[first, second, retry]) as submit:
            self.request(1, "inspect_codex", codex="/first/codex")
            self.request(2, "inspect_codex", codex="/second/codex")
            self.assertEqual([call.args for call in submit.call_args_list],
                             [(inspect_codex, "/first/codex"), (inspect_codex, "/second/codex")])
            first.set_result({"version": "0.164.0"})
            second.set_exception(OSError("Unavailable executable"))
            self.assertEqual(self.messages[1], {"id": 2, "error": "Unavailable executable"})
            self.request(3, "inspect_codex", codex="/second/codex")
            retry.set_result({"version": "0.165.0"})
            self.assertEqual(self.messages[2], {"id": 3, "result": {"version": "0.165.0"}})

    def test_inspection_does_not_bypass_duplicate_session_operation_guard(self):
        inspection = Future()
        with patch.object(self.surface.workers, "submit", return_value=inspection) as submit, \
                patch.object(self.surface.attachments, "attach", return_value={"slot": 0}) as attach, \
                patch.object(self.surface.attachments, "detach") as detach:
            self.request(1, "attach_conversation", thread_id="example")
            task = submit.call_args.args[0]
            self.request(2, "inspect_codex")
            self.request(3, "detach_conversation", thread_id="example")
            self.assertEqual(submit.call_count, 2)
            self.assertEqual(self.messages, [{"id": 3, "error": "A session operation is already running."}])
            task()
            inspection.set_result({"version": "0.165.0"})
            attach.assert_called_once_with("example")
            detach.assert_not_called()
            self.assertFalse(self.surface.tool_pending)


@skipUnless(os.environ.get("PAD_LATTICE_TEST_ENGINE"), "Set PAD_LATTICE_TEST_ENGINE for packaged tests")
class FrozenDesktopTest(TestCase):
    def test_relocated_engine(self):
        with TemporaryDirectory(prefix="pl frozen ") as directory:
            root = Path(directory)
            original = Path(os.environ["PAD_LATTICE_TEST_ENGINE"]).resolve()
            shutil.copytree(original.parent, root / "engine")
            executable = root / "engine" / original.name
            engine = EngineHarness([str(executable)], root)
            try:
                snapshot = engine.request("snapshot")
                self.assertTrue(snapshot["messages"][0]["admin"])
                for removed in ("session", "codex-hook"):
                    result = subprocess.run([str(executable), removed], capture_output=True, timeout=5, cwd=root)
                    self.assertNotEqual(result.returncode, 0)
            finally:
                engine.close()
