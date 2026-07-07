"""Pad-Lattice daemon: Launchpad owner and local socket control plane."""

from __future__ import annotations

import os
import selectors
import socket
import time
from dataclasses import dataclass
from typing import Any

from pad_lattice.events import AgentState, ControlAction
from pad_lattice.launchpad import RUNNING_ACTIVITY_INTERVAL, LaunchpadSurface
from pad_lattice.protocol import (
    ProtocolError,
    action_message,
    decode_message,
    encode_message,
    parse_state,
)


@dataclass
class Client:
    socket: socket.socket
    buffer: bytes = b""
    subscribed_to_actions: bool = False


class PadLatticeDaemon:
    """Own a Launchpad surface and expose state/action messages over a Unix socket."""

    def __init__(
        self,
        surface: LaunchpadSurface,
        socket_path: str,
        *,
        poll_interval: float = 0.03,
        terminal_hold: float = 2.0,
    ) -> None:
        self.surface = surface
        self.socket_path = socket_path
        self.poll_interval = poll_interval
        self.terminal_hold = terminal_hold
        self.state = AgentState.WAITING_FOR_REPLY
        self._selector = selectors.DefaultSelector()
        self._server: socket.socket | None = None
        self._clients: dict[int, Client] = {}
        self._frame = 0
        self._last_rendered_state: AgentState | None = None
        self._next_activity_render = 0.0
        self._terminal_state_until: float | None = None

    def run(self) -> None:
        self._server = self._open_server()
        self._selector.register(self._server, selectors.EVENT_READ, self._accept_client)
        self.surface.initialize()

        try:
            while True:
                self._render_if_needed()
                for key, _ in self._selector.select(timeout=self.poll_interval):
                    callback = key.data
                    callback(key.fileobj)
                self.surface.poll_controls(self._handle_action)
        finally:
            self.close()

    def close(self) -> None:
        for client in list(self._clients.values()):
            self._close_client(client)
        if self._server is not None:
            try:
                self._selector.unregister(self._server)
            except Exception:
                pass
            self._server.close()
            self._server = None
        self._selector.close()
        try:
            os.unlink(self.socket_path)
        except FileNotFoundError:
            pass
        self.surface.clear()

    def handle_message(self, client: Client, message: dict[str, Any]) -> None:
        message_type = message.get("type")
        if message_type == "state":
            self.set_state(parse_state(message.get("state")))
            return
        if message_type == "subscribe_actions":
            client.subscribed_to_actions = True
            return
        if message_type == "ping":
            self._send(client, {"type": "pong"})
            return
        raise ProtocolError(f"unknown message type: {message_type}")

    def set_state(self, state: AgentState) -> None:
        self.state = state
        if state in {AgentState.SUCCESS, AgentState.ERROR}:
            self._terminal_state_until = time.monotonic() + self.terminal_hold
        else:
            self._terminal_state_until = None

    def _open_server(self) -> socket.socket:
        try:
            os.unlink(self.socket_path)
        except FileNotFoundError:
            pass

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(self.socket_path)
        server.listen()
        server.setblocking(False)
        return server

    def _accept_client(self, server: socket.socket) -> None:
        client_socket, _ = server.accept()
        client_socket.setblocking(False)
        client = Client(client_socket)
        self._clients[client_socket.fileno()] = client
        self._selector.register(client_socket, selectors.EVENT_READ, self._read_client)

    def _read_client(self, client_socket: socket.socket) -> None:
        client = self._clients[client_socket.fileno()]
        data = client_socket.recv(4096)
        if not data:
            self._close_client(client)
            return

        client.buffer += data
        while b"\n" in client.buffer:
            line, client.buffer = client.buffer.split(b"\n", 1)
            if not line.strip():
                continue
            try:
                self.handle_message(client, decode_message(line))
            except ProtocolError as exc:
                self._send(client, {"type": "error", "error": str(exc)})

    def _handle_action(self, action: ControlAction) -> None:
        message = action_message(action)
        for client in list(self._clients.values()):
            if client.subscribed_to_actions:
                self._send(client, message)

    def _render_if_needed(self) -> None:
        now = time.monotonic()
        if (
            self._terminal_state_until is not None
            and now >= self._terminal_state_until
        ):
            self.state = AgentState.WAITING_FOR_REPLY
            self._terminal_state_until = None

        refresh_running = (
            self.state is AgentState.RUNNING
            and self._last_rendered_state is AgentState.RUNNING
            and now >= self._next_activity_render
        )
        if self.state != self._last_rendered_state or refresh_running:
            self.surface.render_state_frame(self.state, self._frame)
            self.surface.render_controls()
            self._frame += 1
            self._last_rendered_state = self.state
            self._next_activity_render = now + RUNNING_ACTIVITY_INTERVAL

    def _send(self, client: Client, message: dict[str, Any]) -> None:
        try:
            client.socket.sendall(encode_message(message))
        except OSError:
            self._close_client(client)

    def _close_client(self, client: Client) -> None:
        fileno = client.socket.fileno()
        if fileno in self._clients:
            del self._clients[fileno]
        try:
            self._selector.unregister(client.socket)
        except Exception:
            pass
        client.socket.close()
