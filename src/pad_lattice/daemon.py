"""Pad-Lattice daemon: device owner and multi-agent control plane."""

from __future__ import annotations

import os
import selectors
import socket
import time
from dataclasses import dataclass, field
from typing import Any

from pad_lattice.devices.base import (
    ActionPressed,
    ControlSurface,
    SessionIndicator,
    SessionSelected,
    SurfaceEvent,
    SurfaceView,
)
from pad_lattice.devices.midi_grid import RUNNING_ACTIVITY_INTERVAL
from pad_lattice.events import DEFAULT_AGENT, AgentIdentity, AgentState, ControlAction
from pad_lattice.protocol import (
    ProtocolError,
    action_message,
    decode_message,
    encode_message,
    parse_actions,
    parse_agent,
    parse_state,
)


@dataclass
class Client:
    socket: socket.socket
    buffer: bytes = b""
    agent: AgentIdentity | None = None
    actions: frozenset[ControlAction] = field(default_factory=frozenset)


@dataclass
class AgentSession:
    identity: AgentIdentity
    state: AgentState = AgentState.WAITING_FOR_REPLY
    slot: int | None = None
    last_seen: int = 0
    metadata: dict[str, str] = field(default_factory=dict)
    terminal_state_until: float | None = None


class PadLatticeDaemon:
    """Own one surface and route state/actions for multiple agent sessions."""

    def __init__(
        self,
        surface: ControlSurface,
        socket_path: str,
        *,
        poll_interval: float = 0.03,
        terminal_hold: float = 2.0,
        action_debounce: float = 0.25,
    ) -> None:
        self.surface = surface
        self.socket_path = socket_path
        self.poll_interval = poll_interval
        self.terminal_hold = terminal_hold
        self.action_debounce = action_debounce
        self._selector = selectors.DefaultSelector()
        self._server: socket.socket | None = None
        self._clients: dict[int, Client] = {}
        self._sessions: dict[AgentIdentity, AgentSession] = {}
        self._slots: list[AgentIdentity | None] = [None] * surface.selector_capacity
        self._selected_agent: AgentIdentity | None = None
        self._sequence = 0
        self._frame = 0
        self._render_dirty = True
        self._next_activity_render = 0.0
        self._last_action_at: dict[tuple[AgentIdentity, ControlAction], float] = {}
        self._closed = False

    @property
    def state(self) -> AgentState:
        session = self.selected_session
        return session.state if session is not None else AgentState.WAITING_FOR_REPLY

    @property
    def selected_agent(self) -> AgentIdentity | None:
        return self._selected_agent

    @property
    def selected_session(self) -> AgentSession | None:
        if self._selected_agent is None:
            return None
        return self._sessions.get(self._selected_agent)

    @property
    def sessions(self) -> tuple[AgentSession, ...]:
        return tuple(sorted(self._sessions.values(), key=lambda session: session.last_seen))

    def run(self) -> None:
        self._server = self._open_server()
        self._selector.register(self._server, selectors.EVENT_READ, self._accept_client)
        try:
            self.surface.initialize()
            while True:
                self._render_if_needed()
                for key, _ in self._selector.select(timeout=self.poll_interval):
                    callback = key.data
                    callback(key.fileobj)
                for event in self.surface.poll_events():
                    self._handle_surface_event(event)
        finally:
            self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
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
        self.surface.close()

    def handle_message(self, client: Client, message: dict[str, Any]) -> None:
        message_type = message.get("type")
        if message_type == "state":
            identity = parse_agent(message.get("agent"))
            metadata = _agent_metadata(message.get("agent"))
            self.update_agent(identity, parse_state(message.get("state")), metadata=metadata)
            return
        if message_type == "subscribe_actions":
            identity = parse_agent(message.get("agent"))
            client.agent = identity
            client.actions = parse_actions(message.get("actions"))
            self._ensure_session(identity)
            self._render_dirty = True
            return
        if message_type == "ping":
            self._send(client, {"type": "pong"})
            return
        raise ProtocolError(f"unknown message type: {message_type}")

    def set_state(self, state: AgentState) -> None:
        """Update the default local session used by manual state commands."""

        self.update_agent(DEFAULT_AGENT, state)

    def update_agent(
        self,
        identity: AgentIdentity,
        state: AgentState,
        *,
        metadata: dict[str, str] | None = None,
    ) -> None:
        session = self._ensure_session(identity)
        self._sequence += 1
        session.last_seen = self._sequence
        session.state = state
        if metadata:
            session.metadata.update(metadata)
        if state in {AgentState.SUCCESS, AgentState.ERROR}:
            session.terminal_state_until = time.monotonic() + self.terminal_hold
        else:
            session.terminal_state_until = None
        if session.slot is None:
            self._assign_slot(session)
        self._render_dirty = True

    def select_slot(self, slot: int) -> bool:
        if not 0 <= slot < len(self._slots):
            return False
        identity = self._slots[slot]
        if identity is None:
            return False
        self._selected_agent = identity
        self._render_dirty = True
        return True

    def _ensure_session(self, identity: AgentIdentity) -> AgentSession:
        session = self._sessions.get(identity)
        if session is not None:
            return session
        self._sequence += 1
        session = AgentSession(identity=identity, last_seen=self._sequence)
        self._sessions[identity] = session
        self._assign_slot(session)
        if self._selected_agent is None:
            self._selected_agent = identity
        self._render_dirty = True
        return session

    def _assign_slot(self, session: AgentSession) -> None:
        if session.slot is not None:
            return
        try:
            slot = self._slots.index(None)
        except ValueError:
            candidates = [
                candidate
                for candidate in self._sessions.values()
                if candidate.slot is not None
                and candidate.identity != self._selected_agent
                and candidate.state is not AgentState.WAITING_FOR_APPROVAL
            ]
            if not candidates:
                return
            evicted = min(candidates, key=lambda candidate: candidate.last_seen)
            assert evicted.slot is not None
            slot = evicted.slot
            evicted.slot = None
        self._slots[slot] = session.identity
        session.slot = slot

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

    def _handle_surface_event(self, event: SurfaceEvent) -> None:
        if isinstance(event, SessionSelected):
            self.select_slot(event.slot)
        elif isinstance(event, ActionPressed):
            self._handle_action(event.action)

    def _handle_action(self, action: ControlAction) -> None:
        identity = self._selected_agent
        if identity is None:
            return
        recipients = [
            client
            for client in self._clients.values()
            if client.agent == identity and action in client.actions
        ]
        if not recipients:
            return

        now = time.monotonic()
        debounce_key = (identity, action)
        last_action_at = self._last_action_at.get(debounce_key)
        if last_action_at is not None and now - last_action_at < self.action_debounce:
            return
        self._last_action_at[debounce_key] = now

        message = action_message(action, identity)
        for client in recipients:
            self._send(client, message)

    def _render_if_needed(self) -> None:
        now = time.monotonic()
        for session in self._sessions.values():
            if session.terminal_state_until is not None and now >= session.terminal_state_until:
                session.state = AgentState.WAITING_FOR_REPLY
                session.terminal_state_until = None
                self._render_dirty = True

        refresh_running = self.state is AgentState.RUNNING and now >= self._next_activity_render
        if not self._render_dirty and not refresh_running:
            return

        self.surface.render(self._surface_view())
        self._frame += 1
        self._render_dirty = False
        self._next_activity_render = now + RUNNING_ACTIVITY_INTERVAL

    def _surface_view(self) -> SurfaceView:
        indicators = tuple(
            SessionIndicator(
                slot=session.slot,
                state=session.state,
                selected=session.identity == self._selected_agent,
            )
            for session in sorted(
                (session for session in self._sessions.values() if session.slot is not None),
                key=lambda session: session.slot if session.slot is not None else -1,
            )
            if session.slot is not None
        )
        return SurfaceView(
            selected_state=self.state,
            frame=self._frame,
            sessions=indicators,
            available_actions=self._available_actions(),
        )

    def _available_actions(self) -> frozenset[ControlAction]:
        identity = self._selected_agent
        if identity is None:
            return frozenset()
        return frozenset(
            action
            for client in self._clients.values()
            if client.agent == identity
            for action in client.actions
        )

    def _send(self, client: Client, message: dict[str, Any]) -> None:
        try:
            client.socket.sendall(encode_message(message))
        except OSError:
            self._close_client(client)

    def _close_client(self, client: Client) -> None:
        fileno = client.socket.fileno()
        if fileno in self._clients:
            del self._clients[fileno]
        if client.actions:
            self._render_dirty = True
        try:
            self._selector.unregister(client.socket)
        except Exception:
            pass
        client.socket.close()


def _agent_metadata(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        key: item
        for key, item in value.items()
        if key not in {"backend", "session_id"} and isinstance(item, str) and item
    }
