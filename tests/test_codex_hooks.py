from __future__ import annotations

import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from pad_lattice.codex_hooks import (
    HOOK_COMMAND,
    HOOK_EVENTS,
    install_codex_hooks,
    run_codex_hook,
    state_for_codex_hook,
)
from pad_lattice.events import AgentState


class CodexHookTest(TestCase):
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
        self.assertEqual(output.getvalue(), "{}\n")
        self.assertEqual(
            sent,
            [
                (
                    "/tmp/pad-lattice.sock",
                    {
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
            io.StringIO('{"hook_event_name":"Stop"}'),
            output,
            sender=unavailable,
        )

        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue(), "{}\n")

    def test_invalid_input_is_a_noop(self) -> None:
        output = io.StringIO()

        result = run_codex_hook(
            "/tmp/pad-lattice.sock",
            io.StringIO("not-json"),
            output,
            sender=lambda path, message: self.fail("unexpected state message"),
        )

        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue(), "{}\n")


class CodexHookInstallerTest(TestCase):
    def test_installs_all_hooks_and_preserves_existing_config(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "hooks.json"
            path.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "Stop": [
                                {
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": "existing-hook",
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )

            self.assertTrue(install_codex_hooks(path))
            config = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(
                config["hooks"]["Stop"][0]["hooks"][0]["command"],
                "existing-hook",
            )
            for event_name in HOOK_EVENTS:
                commands = [
                    handler["command"]
                    for group in config["hooks"][event_name]
                    for handler in group["hooks"]
                ]
                self.assertIn(HOOK_COMMAND, commands)

    def test_install_is_idempotent(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "hooks.json"

            self.assertTrue(install_codex_hooks(path))
            first_content = path.read_text(encoding="utf-8")
            self.assertFalse(install_codex_hooks(path))

            self.assertEqual(path.read_text(encoding="utf-8"), first_content)

    def test_rejects_invalid_existing_json(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "hooks.json"
            path.write_text("not-json", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "invalid JSON"):
                install_codex_hooks(path)
