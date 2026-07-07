"""Codex CLI supervision through a terminal PTY and Launchpad controls."""

from __future__ import annotations

import codecs
import os
import pty
import re
import selectors
import signal
import subprocess
import sys
import termios
import time
import tty
from dataclasses import dataclass
from typing import Any

from pad_lattice.events import AgentState, ControlAction

ANSI_ESCAPE_RE = re.compile(rb"\x1b\[[0-?]*[ -/]*[@-~]")
APPROVAL_PATTERNS = (
    "approval",
    "approve",
    "allow",
    "do you want to",
    "waiting for approval",
    "requires approval",
)


@dataclass(frozen=True)
class CodexKeymap:
    approve: bytes = b"\n"
    reject: bytes = b"\x1b"
    retry: bytes = b"r\n"


def decode_key_sequence(value: str) -> bytes:
    """Decode CLI key strings like ``\\n`` and ``\\x1b`` into bytes."""

    return codecs.decode(value, "unicode_escape").encode()


def build_codex_command(args: list[str]) -> list[str]:
    if args and args[0] == "--":
        args = args[1:]
    return ["codex", *args]


def detect_codex_state(output: bytes, current_state: AgentState) -> AgentState:
    text = ANSI_ESCAPE_RE.sub(b"", output).decode("utf-8", "ignore").lower()
    if any(pattern in text for pattern in APPROVAL_PATTERNS):
        return AgentState.WAITING_FOR_APPROVAL
    if current_state is AgentState.WAITING_FOR_APPROVAL and text.strip():
        return AgentState.RUNNING
    return current_state


class CodexSupervisor:
    def __init__(
        self,
        command: list[str],
        *,
        surface: Any | None = None,
        keymap: CodexKeymap | None = None,
        poll_interval: float = 0.03,
        animation_interval: float = 0.12,
    ) -> None:
        self.command = command
        self.surface = surface
        self.keymap = keymap or CodexKeymap()
        self.poll_interval = poll_interval
        self.animation_interval = animation_interval
        self.state = AgentState.RUNNING
        self._master_fd: int | None = None
        self._process: subprocess.Popen[bytes] | None = None

    def run(self) -> int:
        master_fd, slave_fd = pty.openpty()
        self._master_fd = master_fd
        self._process = subprocess.Popen(
            self.command,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            preexec_fn=os.setsid,
        )
        os.close(slave_fd)

        old_termios = None
        stdin_fd = sys.stdin.fileno()
        stdout_fd = sys.stdout.fileno()
        stdin_is_tty = os.isatty(stdin_fd)
        if stdin_is_tty:
            old_termios = termios.tcgetattr(stdin_fd)
            tty.setraw(stdin_fd)

        selector = selectors.DefaultSelector()
        selector.register(master_fd, selectors.EVENT_READ, "codex")
        if stdin_is_tty:
            selector.register(stdin_fd, selectors.EVENT_READ, "stdin")

        frame = 0
        next_render = 0.0

        if self.surface is not None:
            self.surface.initialize()

        try:
            while True:
                now = time.monotonic()
                if self.surface is not None and now >= next_render:
                    self.surface.render_state_frame(self.state, frame)
                    self.surface.render_controls()
                    frame += 1
                    next_render = now + self.animation_interval

                for key, _ in selector.select(timeout=self.poll_interval):
                    if key.data == "codex":
                        if not self._read_codex_output(master_fd, stdout_fd):
                            return self._finish()
                    elif key.data == "stdin":
                        data = os.read(stdin_fd, 4096)
                        if data:
                            os.write(master_fd, data)

                if self.surface is not None:
                    self.surface.poll_controls(self.handle_action)

                if self._process.poll() is not None:
                    return self._finish()
        finally:
            selector.close()
            if old_termios is not None:
                termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_termios)
            if self.surface is not None:
                self.surface.clear()
            os.close(master_fd)
            self._master_fd = None

    def handle_action(self, action: ControlAction) -> None:
        if action is ControlAction.APPROVE:
            self._write_to_codex(self.keymap.approve)
            self.state = AgentState.RUNNING
        elif action is ControlAction.REJECT:
            self._write_to_codex(self.keymap.reject)
            self.state = AgentState.RUNNING
        elif action is ControlAction.RETRY:
            self._write_to_codex(self.keymap.retry)
            self.state = AgentState.RUNNING
        elif action is ControlAction.STOP:
            self._interrupt_codex()
            self.state = AgentState.ERROR

    def _read_codex_output(self, master_fd: int, stdout_fd: int) -> bool:
        try:
            data = os.read(master_fd, 4096)
        except OSError:
            return False
        if not data:
            return False

        os.write(stdout_fd, data)
        self.state = detect_codex_state(data, self.state)
        return True

    def _write_to_codex(self, data: bytes) -> None:
        if self._master_fd is not None:
            os.write(self._master_fd, data)

    def _interrupt_codex(self) -> None:
        if self._process is not None and self._process.poll() is None:
            os.killpg(self._process.pid, signal.SIGINT)

    def _finish(self) -> int:
        if self._process is None:
            return 1
        return_code = self._process.poll()
        if return_code is None:
            return_code = self._process.wait()
        self.state = AgentState.SUCCESS if return_code == 0 else AgentState.ERROR
        return return_code
