from __future__ import annotations

from unittest import TestCase

from pad_lattice.codex_cli import (
    CodexKeymap,
    CodexSupervisor,
    build_codex_command,
    decode_key_sequence,
    detect_codex_state,
)
from pad_lattice.events import AgentState, ControlAction


class CodexCliTest(TestCase):
    def test_build_codex_command_strips_remainder_separator(self) -> None:
        self.assertEqual(
            build_codex_command(["--", "resume", "--last"]),
            ["codex", "resume", "--last"],
        )

    def test_decode_key_sequence_accepts_python_escapes(self) -> None:
        self.assertEqual(decode_key_sequence("\\n"), b"\n")
        self.assertEqual(decode_key_sequence("\\x1b"), b"\x1b")

    def test_detect_codex_state_finds_approval_prompt(self) -> None:
        self.assertIs(
            detect_codex_state(b"Do you want to allow this command?", AgentState.RUNNING),
            AgentState.WAITING_FOR_APPROVAL,
        )

    def test_detect_codex_state_returns_to_running_after_prompt_output(self) -> None:
        self.assertIs(
            detect_codex_state(b"running command", AgentState.WAITING_FOR_APPROVAL),
            AgentState.RUNNING,
        )

    def test_handle_action_writes_configured_keys(self) -> None:
        writes = []
        supervisor = CodexSupervisor(
            ["codex"],
            keymap=CodexKeymap(approve=b"a", reject=b"r", retry=b"t"),
        )
        supervisor._write_to_codex = writes.append

        supervisor.handle_action(ControlAction.APPROVE)
        supervisor.handle_action(ControlAction.REJECT)
        supervisor.handle_action(ControlAction.RETRY)

        self.assertEqual(writes, [b"a", b"r", b"t"])
