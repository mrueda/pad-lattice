from __future__ import annotations

import fcntl
import os
import pty
import struct
import termios
from unittest import TestCase

from pad_lattice.codex_cli import (
    CodexKeymap,
    CodexSupervisor,
    TerminalSize,
    build_codex_command,
    decode_key_sequence,
    detect_codex_state,
    set_pty_size,
    state_after_user_input,
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

    def test_detect_codex_state_finds_reply_prompt(self) -> None:
        self.assertIs(
            detect_codex_state(b"What would you like to do next?", AgentState.RUNNING),
            AgentState.WAITING_FOR_REPLY,
        )

    def test_detect_codex_state_keeps_approval_waiting_during_redraw_output(self) -> None:
        self.assertIs(
            detect_codex_state(b"running command", AgentState.WAITING_FOR_APPROVAL),
            AgentState.WAITING_FOR_APPROVAL,
        )

    def test_detect_codex_state_keeps_reply_waiting_during_redraw_output(self) -> None:
        self.assertIs(
            detect_codex_state(b"working again", AgentState.WAITING_FOR_REPLY),
            AgentState.WAITING_FOR_REPLY,
        )

    def test_state_after_user_input_marks_reply_as_typing_before_enter(self) -> None:
        self.assertIs(
            state_after_user_input(AgentState.WAITING_FOR_REPLY, b"h"),
            AgentState.USER_TYPING,
        )

    def test_state_after_user_input_marks_typing_as_running_on_enter(self) -> None:
        self.assertIs(
            state_after_user_input(AgentState.USER_TYPING, b"\r"),
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

    def test_set_pty_size_updates_terminal_window_size(self) -> None:
        master_fd, slave_fd = pty.openpty()
        try:
            set_pty_size(slave_fd, TerminalSize(rows=33, columns=111))
            packed = fcntl.ioctl(slave_fd, termios.TIOCGWINSZ, b"\0" * 8)
            rows, columns, _, _ = struct.unpack("HHHH", packed)

            self.assertEqual((rows, columns), (33, 111))
        finally:
            os.close(master_fd)
            os.close(slave_fd)
