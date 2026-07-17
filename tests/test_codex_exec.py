from __future__ import annotations

import io
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from pad_lattice.codex_exec import run_codex_exec, state_for_codex_event
from pad_lattice.events import AgentState


class CodexExecTest(TestCase):
    def test_turn_started_maps_to_running(self) -> None:
        self.assertIs(
            state_for_codex_event({"type": "turn.started"}),
            AgentState.RUNNING,
        )

    def test_turn_completed_maps_to_success(self) -> None:
        self.assertIs(
            state_for_codex_event({"type": "turn.completed"}),
            AgentState.SUCCESS,
        )

    def test_error_maps_to_error(self) -> None:
        self.assertIs(
            state_for_codex_event({"type": "error"}),
            AgentState.ERROR,
        )

    def test_agent_message_does_not_change_state(self) -> None:
        self.assertIsNone(
            state_for_codex_event(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": "done"},
                }
            )
        )

    def test_run_assigns_one_identity_to_all_state_messages(self) -> None:
        process = SimpleNamespace(
            stdout=io.StringIO(
                '{"type":"turn.started"}\n'
                '{"type":"turn.completed"}\n'
            ),
            wait=lambda: 0,
            poll=lambda: 0,
        )
        sent = []
        thread = SimpleNamespace(start=lambda: None)

        with (
            patch("pad_lattice.codex_exec.subprocess.Popen", return_value=process),
            patch("pad_lattice.codex_exec.threading.Thread", return_value=thread),
            patch(
                "pad_lattice.codex_exec.uuid.uuid4",
                return_value=SimpleNamespace(hex="agent-123"),
            ),
        ):
            result = run_codex_exec(
                ["say hello"],
                "/tmp/pad-lattice.sock",
                sender=lambda path, message: sent.append(message),
                stdout=io.StringIO(),
                stderr=io.StringIO(),
            )

        self.assertEqual(result, 0)
        self.assertEqual({message["agent"]["session_id"] for message in sent}, {"agent-123"})
        self.assertEqual({message["agent"]["backend"] for message in sent}, {"codex-exec"})

    def test_spawn_failure_reports_error_for_the_same_identity(self) -> None:
        sent = []

        with (
            patch(
                "pad_lattice.codex_exec.subprocess.Popen",
                side_effect=FileNotFoundError("codex"),
            ),
            patch(
                "pad_lattice.codex_exec.uuid.uuid4",
                return_value=SimpleNamespace(hex="agent-123"),
            ),
            self.assertRaises(FileNotFoundError),
        ):
            run_codex_exec(
                ["say hello"],
                "/tmp/pad-lattice.sock",
                sender=lambda path, message: sent.append(message),
                stdout=io.StringIO(),
                stderr=io.StringIO(),
            )

        self.assertEqual([message["state"] for message in sent], ["running", "error"])
        self.assertEqual({message["agent"]["session_id"] for message in sent}, {"agent-123"})
