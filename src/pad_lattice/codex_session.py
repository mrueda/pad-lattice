"""Interactive Codex launcher with a daemon-owned session lease."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from pad_lattice.codex_hooks import (
    DEFAULT_APPROVAL_TIMEOUT,
    codex_hook_config_overrides,
    resolve_hook_command,
)
from pad_lattice.events import AgentIdentity
from pad_lattice.protocol import (
    JsonLineConnection,
    ProtocolError,
    parse_agent,
    session_lease_message,
)

MAX_LABEL_LENGTH = 64
LEASE_RETRY_INTERVAL = 1.0
LEASE_CONNECT_WAIT = 0.25


def normalize_session_label(label: str | None) -> str | None:
    """Validate a label before it can reach terminal titles or status output."""

    if label is None:
        return None
    normalized = label.strip()
    if not normalized:
        raise ValueError("session label must not be empty")
    if len(normalized) > MAX_LABEL_LENGTH:
        raise ValueError(
            f"session label must be at most {MAX_LABEL_LENGTH} characters"
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise ValueError("session label must not contain control characters")
    return normalized


class SessionLease:
    """Keep a daemon connection open for the lifetime of one Codex process."""

    def __init__(
        self,
        socket_path: str,
        lease_id: str,
        metadata: dict[str, str],
        *,
        retry_interval: float = LEASE_RETRY_INTERVAL,
    ) -> None:
        self.socket_path = socket_path
        self.lease_id = lease_id
        self.metadata = dict(metadata)
        self.retry_interval = retry_interval
        self._stop = threading.Event()
        self._attempted = threading.Event()
        self._connected = threading.Event()
        self._thread: threading.Thread | None = None
        self._socket: socket.socket | None = None
        self._known_agent: AgentIdentity | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run,
            name=f"pad-lattice-lease-{self.lease_id[:8]}",
            daemon=True,
        )
        self._thread.start()

    def wait_for_first_attempt(self, timeout: float = LEASE_CONNECT_WAIT) -> bool:
        self._attempted.wait(timeout)
        return self._connected.is_set()

    def close(self) -> None:
        self._stop.set()
        with self._lock:
            active_socket = self._socket
        if active_socket is not None:
            try:
                active_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._run_connection()
            except OSError:
                self._connected.clear()
                self._attempted.set()
            if not self._stop.wait(self.retry_interval):
                continue
            break

    def _run_connection(self) -> None:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(1.0)
            client.connect(self.socket_path)
            with self._lock:
                self._socket = client
                known_agent = self._known_agent
            connection = JsonLineConnection(client)
            connection.send(
                session_lease_message(
                    self.lease_id,
                    agent=known_agent,
                    metadata=self.metadata,
                )
            )
            self._connected.set()
            self._attempted.set()
            try:
                while not self._stop.is_set():
                    try:
                        message = connection.receive()
                    except socket.timeout:
                        continue
                    except ProtocolError:
                        continue
                    except ConnectionError:
                        return
                    self._remember_binding(message)
            finally:
                self._connected.clear()
                with self._lock:
                    if self._socket is client:
                        self._socket = None

    def _remember_binding(self, message: dict[str, object]) -> None:
        session = message.get("session")
        if not isinstance(session, dict):
            return
        try:
            identity = parse_agent(session, default=None)
        except ProtocolError:
            return
        with self._lock:
            self._known_agent = identity


def run_codex_session(
    codex_args: Sequence[str],
    socket_path: str,
    *,
    label: str | None = None,
    codex_binary: str = "codex",
    terminal_title: bool = True,
    approval_timeout: float = DEFAULT_APPROVAL_TIMEOUT,
    hook_command: str | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run interactive Codex with inherited stdio and a reconnecting lease."""

    if stderr is None:
        stderr = sys.stderr
    normalized_label = normalize_session_label(label)
    lease_id = uuid.uuid4().hex
    metadata = {"cwd": str(Path.cwd())}
    if normalized_label is not None:
        metadata["label"] = normalized_label

    lease = SessionLease(socket_path, lease_id, metadata)
    lease.start()
    connected = lease.wait_for_first_attempt()

    environment = os.environ.copy()
    environment["PAD_LATTICE_LEASE_ID"] = lease_id
    environment["PAD_LATTICE_SOCKET"] = socket_path
    environment.pop("PAD_LATTICE_LABEL", None)
    environment.pop("PAD_LATTICE_TERMINAL_TITLE", None)
    if normalized_label is not None:
        environment["PAD_LATTICE_LABEL"] = normalized_label
    if terminal_title:
        environment["PAD_LATTICE_TERMINAL_TITLE"] = "1"

    if hook_command is None:
        hook_command = resolve_hook_command(
            socket_path,
            approval_timeout=approval_timeout,
        )

    command = [codex_binary, "--enable", "hooks"]
    for override in codex_hook_config_overrides(
        hook_command,
        approval_timeout=approval_timeout,
    ):
        command.extend(["-c", override])
    if terminal_title:
        command.extend(["-c", "tui.terminal_title=[]"])
    command.extend(codex_args)

    if not connected:
        print(
            "pad-lattice: daemon unavailable; Codex will start and the lease will retry",
            file=stderr,
        )
    try:
        process = subprocess.Popen(command, env=environment)
        return process.wait()
    finally:
        lease.close()
