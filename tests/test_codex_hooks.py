from __future__ import annotations

import io
import json
import shlex
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from pad_lattice.codex_hook_entry import main as run_codex_hook_entry
from pad_lattice.codex_hooks import (
    HOOK_EVENTS,
    _wait_for_permission_action_client,
    codex_hook_config_overrides,
    installed_codex_hook_events,
    remove_codex_hooks,
    resolve_hook_command,
    run_codex_hook,
    state_for_codex_hook,
)
from pad_lattice.events import AgentIdentity, AgentState, ControlAction
from pad_lattice.protocol import (
    WIRE_PROTOCOL_VERSION,
    ProtocolError,
    action_message,
    decode_message,
    encode_message,
)


HOOK_COMMAND = (
    "pad-lattice-hook --socket /tmp/pad-lattice.sock "
    "--approval-timeout 60"
)
LEGACY_HOOK_COMMAND = (
    "pad-lattice codex-hook --socket /tmp/pad-lattice.sock "
    "--approval-timeout 60"
)


class CodexHookTest(TestCase):
    def setUp(self) -> None:
        environment = patch.dict("os.environ", {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def test_maps_supported_lifecycle_events(self) -> None:
        expected = {
            "SessionStart": AgentState.WAITING_FOR_REPLY,
            "UserPromptSubmit": AgentState.RUNNING,
            "PermissionRequest": AgentState.WAITING_FOR_APPROVAL,
            "PostToolUse": AgentState.RUNNING,
            "Stop": AgentState.SUCCESS,
        }

        for event_name, state in expected.items():
            with self.subTest(event_name=event_name):
                self.assertIs(
                    state_for_codex_hook({"hook_event_name": event_name}),
                    state,
                )

    def test_ignores_unknown_events(self) -> None:
        self.assertIsNone(state_for_codex_hook({"hook_event_name": "PreCompact"}))

    def test_sends_state_with_codex_session_identity(self) -> None:
        sent = []
        output = io.StringIO()
        event = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "session-123",
            "cwd": "/work/repository",
            "model": "gpt-test",
        }

        result = run_codex_hook(
            "/tmp/pad-lattice.sock",
            io.StringIO(json.dumps(event)),
            output,
            sender=lambda path, message: sent.append((path, message)),
        )

        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(
            sent,
            [
                (
                    "/tmp/pad-lattice.sock",
                    {
                        "protocol": WIRE_PROTOCOL_VERSION,
                        "type": "state",
                        "state": "running",
                        "agent": {
                            "backend": "codex",
                            "session_id": "session-123",
                            "cwd": "/work/repository",
                            "model": "gpt-test",
                        },
                    },
                )
            ],
        )

    def test_daemon_connection_failure_does_not_fail_hook(self) -> None:
        def unavailable(path, message):
            raise FileNotFoundError(path)

        output = io.StringIO()
        result = run_codex_hook(
            "/missing.sock",
            io.StringIO(
                '{"hook_event_name":"Stop","session_id":"session-123"}'
            ),
            output,
            sender=unavailable,
        )

        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue(), "")

    def test_daemon_protocol_failure_does_not_fail_hook(self) -> None:
        def invalid_response(path, message):
            raise ProtocolError("invalid daemon response")

        output = io.StringIO()
        result = run_codex_hook(
            "/tmp/pad-lattice.sock",
            io.StringIO(
                '{"hook_event_name":"PostToolUse","session_id":"session-123"}'
            ),
            output,
            sender=invalid_response,
        )

        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue(), "")

    def test_permission_request_returns_hardware_approval_to_codex(self) -> None:
        sent = []
        waited = []
        output = io.StringIO()
        event = {
            "hook_event_name": "PermissionRequest",
            "session_id": "session-123",
            "cwd": "/work/repository",
        }

        result = run_codex_hook(
            "/tmp/pad-lattice.sock",
            io.StringIO(json.dumps(event)),
            output,
            approval_timeout=60,
            sender=lambda path, message: sent.append(message),
            action_waiter=lambda path, identity, timeout: (
                waited.append((path, identity.session_id, timeout))
                or ControlAction.APPROVE
            ),
        )

        self.assertEqual(result, 0)
        self.assertEqual(
            json.loads(output.getvalue()),
            {
                "hookSpecificOutput": {
                    "hookEventName": "PermissionRequest",
                    "decision": {"behavior": "allow"},
                }
            },
        )
        self.assertEqual(waited, [("/tmp/pad-lattice.sock", "session-123", 60)])
        self.assertEqual(
            [message["state"] for message in sent],
            ["waiting_for_approval", "running"],
        )

    def test_permission_request_can_reject_or_fall_back_to_keyboard(self) -> None:
        event = {
            "hook_event_name": "PermissionRequest",
            "session_id": "session-123",
        }
        rejected = io.StringIO()
        timed_out = io.StringIO()

        run_codex_hook(
            "/tmp/pad-lattice.sock",
            io.StringIO(json.dumps(event)),
            rejected,
            sender=lambda path, message: None,
            action_waiter=lambda path, identity, timeout: ControlAction.REJECT,
        )
        run_codex_hook(
            "/tmp/pad-lattice.sock",
            io.StringIO(json.dumps(event)),
            timed_out,
            sender=lambda path, message: None,
            action_waiter=lambda path, identity, timeout: None,
        )

        self.assertEqual(
            json.loads(rejected.getvalue())["hookSpecificOutput"]["decision"],
            {
                "behavior": "deny",
                "message": "Rejected from Pad-Lattice.",
            },
        )
        self.assertEqual(timed_out.getvalue(), "")

    def test_launcher_environment_overrides_installed_socket_and_labels_state(self) -> None:
        sent = []
        event = {
            "hook_event_name": "SessionStart",
            "session_id": "session-123",
            "cwd": "/work/repository",
        }

        with patch.dict(
            "os.environ",
            {
                "PAD_LATTICE_SOCKET": "/tmp/runtime.sock",
                "PAD_LATTICE_LEASE_ID": "lease-123",
                "PAD_LATTICE_LABEL": "docs",
            },
            clear=False,
        ):
            run_codex_hook(
                "/tmp/installed.sock",
                io.StringIO(json.dumps(event)),
                io.StringIO(),
                sender=lambda path, message: sent.append((path, message)),
            )

        self.assertEqual(sent[0][0], "/tmp/runtime.sock")
        self.assertEqual(sent[0][1]["lease_id"], "lease-123")
        self.assertEqual(sent[0][1]["agent"]["label"], "docs")

    def test_launcher_hook_sets_scene_identity_in_terminal_title(self) -> None:
        event = {
            "hook_event_name": "SessionStart",
            "session_id": "session-123",
            "cwd": "/work/repository",
        }
        requested = []

        with (
            patch.dict(
                "os.environ",
                {
                    "PAD_LATTICE_TERMINAL_TITLE": "1",
                    "PAD_LATTICE_LEASE_ID": "lease-123",
                },
                clear=False,
            ),
            patch("pad_lattice.codex_hooks.os.open", return_value=9),
            patch("pad_lattice.codex_hooks.os.write") as write,
            patch("pad_lattice.codex_hooks.os.close"),
        ):
            run_codex_hook(
                "/tmp/pad-lattice.sock",
                io.StringIO(json.dumps(event)),
                io.StringIO(),
                requester=lambda path, message: (
                    requested.append(message)
                    or {
                        "type": "state_ack",
                        "scene": 2,
                        "accent": "magenta",
                        "label": "repository",
                    }
                ),
            )

        self.assertTrue(requested[0]["reply"])
        self.assertEqual(requested[0]["lease_id"], "lease-123")
        self.assertIn(b"[S2 MAGENTA] repository", write.call_args.args[1])

    def test_permission_waiter_uses_request_scoped_unix_socket_message(self) -> None:
        agent = AgentIdentity("codex", "session-123")
        received = []

        class ApprovalSocket:
            response = b""

            def sendall(self, data: bytes) -> None:
                message = decode_message(data.strip())
                received.append(message)
                self.response = encode_message(
                    action_message(
                        ControlAction.APPROVE,
                        agent,
                        request_id=message["request_id"],
                    )
                )

            def recv(self, size: int) -> bytes:
                response, self.response = self.response, b""
                return response

            def settimeout(self, timeout: float) -> None:
                pass

        action = _wait_for_permission_action_client(ApprovalSocket(), agent, 1.0)

        self.assertIs(action, ControlAction.APPROVE)
        self.assertTrue(received[0]["one_shot"])
        self.assertEqual(received[0]["actions"], ["approve", "reject"])

    def test_invalid_input_is_a_noop(self) -> None:
        output = io.StringIO()

        result = run_codex_hook(
            "/tmp/pad-lattice.sock",
            io.StringIO("not-json"),
            output,
            sender=lambda path, message: self.fail("unexpected state message"),
        )

        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue(), "")

    def test_lightweight_entry_is_silent_when_daemon_is_absent(self) -> None:
        event = io.StringIO(
            '{"hook_event_name":"PostToolUse","session_id":"session-123"}'
        )
        output = io.StringIO()
        checked = []

        result = run_codex_hook_entry(
            [
                "--socket",
                "/missing.sock",
                "--approval-timeout",
                "60",
            ],
            stdin=event,
            stdout=output,
            socket_checker=lambda path: checked.append(path) or False,
        )

        self.assertEqual(result, 0)
        self.assertEqual(checked, ["/missing.sock"])
        self.assertEqual(event.read(), "")
        self.assertEqual(output.getvalue(), "")

    def test_lightweight_entry_delegates_when_daemon_is_available(self) -> None:
        event = io.StringIO(
            '{"hook_event_name":"SessionStart","session_id":"session-123"}'
        )
        output = io.StringIO()

        with patch(
            "pad_lattice.codex_hooks.run_codex_hook",
            return_value=0,
        ) as run_hook:
            result = run_codex_hook_entry(
                ["--socket", "/tmp/pad-lattice.sock"],
                stdin=event,
                stdout=output,
                socket_checker=lambda path: True,
            )

        self.assertEqual(result, 0)
        run_hook.assert_called_once_with(
            "/tmp/pad-lattice.sock",
            event,
            output,
            approval_timeout=60.0,
        )

    def test_lightweight_entry_checks_launcher_socket_override(self) -> None:
        event = io.StringIO("{}")
        checked = []

        with patch.dict(
            "os.environ",
            {"PAD_LATTICE_SOCKET": "/tmp/launcher.sock"},
            clear=False,
        ):
            result = run_codex_hook_entry(
                ["--socket", "/tmp/installed.sock"],
                stdin=event,
                stdout=io.StringIO(),
                socket_checker=lambda path: checked.append(path) or False,
            )

        self.assertEqual(result, 0)
        self.assertEqual(checked, ["/tmp/launcher.sock"])


class CodexHookConfigurationTest(TestCase):
    def test_builds_session_scoped_overrides_for_every_hook(self) -> None:
        command = '/opt/Pad Lattice/pad-lattice-hook --socket "/tmp/pad.sock"'

        overrides = codex_hook_config_overrides(command, approval_timeout=60)

        self.assertEqual(len(overrides), len(HOOK_EVENTS))
        for event_name, override in zip(HOOK_EVENTS, overrides, strict=True):
            self.assertTrue(override.startswith(f"hooks.{event_name}="))
            self.assertIn('type="command"', override)
            self.assertIn(json.dumps(command), override)
            expected_timeout = 65 if event_name == "PermissionRequest" else 5
            self.assertTrue(override.endswith(f"timeout={expected_timeout}}}]}}]"))

    def test_rejects_nonpositive_session_approval_timeout(self) -> None:
        with self.assertRaisesRegex(ValueError, "approval_timeout must be positive"):
            codex_hook_config_overrides(HOOK_COMMAND, approval_timeout=0)

    def test_resolves_absolute_console_script_path(self) -> None:
        with TemporaryDirectory(prefix="pad lattice ") as directory:
            executable = Path(directory) / "pad-lattice"
            executable.touch()
            hook_executable = Path(directory) / "pad-lattice-hook"
            hook_executable.touch()
            socket_path = Path(directory) / "pad-lattice.sock"

            self.assertEqual(
                resolve_hook_command(str(socket_path), str(executable)),
                (
                    f"{shlex.quote(str(hook_executable.resolve()))} "
                    f"--socket {shlex.quote(str(socket_path.resolve()))} "
                    "--approval-timeout 60"
                ),
            )

    def test_falls_back_when_lightweight_console_script_is_unavailable(self) -> None:
        with TemporaryDirectory() as directory:
            executable = Path(directory) / "pad-lattice"
            executable.touch()

            command = resolve_hook_command(
                str(Path(directory) / "pad-lattice.sock"),
                str(executable),
            )

        self.assertIn("pad-lattice codex-hook", command)

    def test_removes_global_hooks_without_touching_other_handlers(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "hooks.json"
            path.write_text(
                json.dumps(
                    {
                        "hooks": {
                            event_name: [
                                {
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": LEGACY_HOOK_COMMAND,
                                        },
                                        {"type": "command", "command": "existing-hook"},
                                    ]
                                }
                            ]
                            for event_name in HOOK_EVENTS
                        },
                        "description": "Keep this metadata.",
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(installed_codex_hook_events(path), HOOK_EVENTS)
            self.assertTrue(remove_codex_hooks(path))
            config = json.loads(path.read_text(encoding="utf-8"))

            for event_name in HOOK_EVENTS:
                handlers = [
                    handler
                    for group in config["hooks"][event_name]
                    for handler in group["hooks"]
                ]
                self.assertEqual(
                    [handler["command"] for handler in handlers],
                    ["existing-hook"],
                )
            self.assertEqual(config["description"], "Keep this metadata.")
            self.assertEqual(installed_codex_hook_events(path), ())

    def test_removing_only_global_hooks_leaves_an_empty_config(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "hooks.json"
            path.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "PostToolUse": [
                                {
                                    "hooks": [
                                        {"type": "command", "command": HOOK_COMMAND}
                                    ]
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )

            self.assertTrue(remove_codex_hooks(path))

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {})
            self.assertFalse(remove_codex_hooks(path))

    def test_global_cleanup_rejects_invalid_existing_json(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "hooks.json"
            path.write_text("not-json", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "invalid JSON"):
                remove_codex_hooks(path)
