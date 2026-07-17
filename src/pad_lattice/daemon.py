"""Pad-Lattice daemon: device owner and multi-agent control plane."""

from __future__ import annotations

import errno
import os
import selectors
import socket
import stat
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
from pad_lattice.events import DEFAULT_AGENT, AgentIdentity, AgentState, ControlAction
from pad_lattice.identity_store import IdentityStore
from pad_lattice.protocol import (
    ProtocolError,
    action_message,
    decode_message,
    encode_message,
    parse_actions,
    parse_agent,
    parse_boolean,
    parse_identifier,
    parse_metadata,
    parse_state,
)
from pad_lattice.visual_protocol import RUNNING_ACTIVITY_INTERVAL

DEFAULT_SESSION_TTL = 24 * 60 * 60.0
TERMINAL_STATES = frozenset(
    {AgentState.SUCCESS, AgentState.ERROR, AgentState.CANCELLED}
)
ACTION_STATES: dict[ControlAction, frozenset[AgentState]] = {
    ControlAction.APPROVE: frozenset({AgentState.WAITING_FOR_APPROVAL}),
    ControlAction.REJECT: frozenset({AgentState.WAITING_FOR_APPROVAL}),
    ControlAction.RETRY: frozenset({AgentState.ERROR, AgentState.CANCELLED}),
    ControlAction.STOP: frozenset({AgentState.RUNNING}),
}


@dataclass
class Client:
    socket: socket.socket
    buffer: bytes = b""
    agent: AgentIdentity | None = None
    actions: frozenset[ControlAction] = field(default_factory=frozenset)
    request_id: str | None = None
    one_shot: bool = False
    subscribed_at: int = 0
    lease_id: str | None = None


@dataclass
class AgentSession:
    identity: AgentIdentity
    state: AgentState = AgentState.WAITING_FOR_REPLY
    slot: int | None = None
    accent: str | None = None
    last_seen: int = 0
    last_activity_at: float = field(default_factory=time.monotonic)
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
        session_ttl: float = DEFAULT_SESSION_TTL,
        activity_motion: bool = False,
        identity_store: IdentityStore | None = None,
    ) -> None:
        if session_ttl < 0:
            raise ValueError("session_ttl must be zero or positive")
        if len(surface.accent_names) != surface.selector_capacity:
            raise ValueError("surface must provide one accent per selector slot")
        if len(set(surface.accent_names)) != len(surface.accent_names):
            raise ValueError("surface accent names must be unique")
        self.surface = surface
        self.socket_path = socket_path
        self.poll_interval = poll_interval
        self.terminal_hold = terminal_hold
        self.action_debounce = action_debounce
        self.session_ttl = session_ttl
        self.activity_motion = activity_motion
        self.identity_store = identity_store
        self._selector = selectors.DefaultSelector()
        self._server: socket.socket | None = None
        self._owns_socket_path = False
        self._clients: dict[int, Client] = {}
        self._sessions: dict[AgentIdentity, AgentSession] = {}
        self._lease_clients: dict[str, Client] = {}
        self._lease_agents: dict[str, AgentIdentity] = {}
        self._lease_metadata: dict[str, dict[str, str]] = {}
        self._slots: list[AgentIdentity | None] = [None] * surface.selector_capacity
        self._selected_agent: AgentIdentity | None = None
        self._sequence = 0
        self._frame = 0
        self._render_dirty = True
        self._next_activity_render = 0.0
        self._last_action_at: dict[tuple[AgentIdentity, ControlAction], float] = {}
        self._closed = False

    @property
    def state(self) -> AgentState | None:
        session = self.selected_session
        return session.state if session is not None else None

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
        if self._owns_socket_path:
            try:
                os.unlink(self.socket_path)
            except FileNotFoundError:
                pass
            self._owns_socket_path = False
        self.surface.close()

    def handle_message(self, client: Client, message: dict[str, Any]) -> None:
        message_type = message.get("type")
        if message_type == "state":
            identity = parse_agent(message.get("agent"))
            metadata = _agent_metadata(message.get("agent"))
            lease_id = parse_identifier(
                message.get("lease_id"), field="lease_id", default=None
            )
            if lease_id is not None:
                self._bind_lease(lease_id, identity, metadata)
            self.update_agent(identity, parse_state(message.get("state")), metadata=metadata)
            if parse_boolean(message.get("reply"), field="reply"):
                self._send(client, self._state_ack(self._sessions[identity]))
            return
        if message_type == "session_lease":
            self._register_lease(client, message)
            return
        if message_type == "subscribe_actions":
            identity = parse_agent(message.get("agent"))
            client.agent = identity
            client.actions = parse_actions(message.get("actions"))
            client.request_id = parse_identifier(
                message.get("request_id"), field="request_id", default=None
            )
            client.one_shot = parse_boolean(
                message.get("one_shot"), field="one_shot"
            )
            session = self._ensure_session(identity)
            self._sequence += 1
            client.subscribed_at = self._sequence
            session.last_seen = self._sequence
            session.last_activity_at = time.monotonic()
            self._render_dirty = True
            return
        if message_type == "session_end":
            self.end_agent(parse_agent(message.get("agent"), default=None))
            return
        if message_type == "status":
            self._send(client, self.status_snapshot())
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
        now = time.monotonic()
        self._sequence += 1
        session.last_seen = self._sequence
        session.last_activity_at = now
        session.state = (
            AgentState.WAITING_FOR_APPROVAL
            if state is not AgentState.WAITING_FOR_APPROVAL
            and self._has_pending_approval(identity)
            else state
        )
        if metadata:
            session.metadata.update(metadata)
        if session.state in TERMINAL_STATES:
            session.terminal_state_until = now + self.terminal_hold
        else:
            session.terminal_state_until = None
        if session.slot is None:
            self._assign_slot(session)
        self._render_dirty = True

    def end_agent(self, identity: AgentIdentity) -> bool:
        session = self._sessions.pop(identity, None)
        if session is None:
            return False
        if session.slot is not None:
            self._slots[session.slot] = None
        if identity == self._selected_agent:
            self._selected_agent = None
        for client in self._clients.values():
            if client.agent == identity:
                client.agent = None
                client.actions = frozenset()
                client.request_id = None
                client.one_shot = False
        for lease_id, agent in list(self._lease_agents.items()):
            if agent == identity:
                del self._lease_agents[lease_id]
        self._last_action_at = {
            key: value
            for key, value in self._last_action_at.items()
            if key[0] != identity
        }
        self._fill_empty_slots()
        self._render_dirty = True
        return True

    def status_snapshot(self) -> dict[str, Any]:
        sessions = sorted(
            self._sessions.values(),
            key=lambda session: (
                session.slot is None,
                session.slot if session.slot is not None else session.last_seen,
            ),
        )
        return {
            "type": "status",
            "profile": self.surface.profile_id,
            "visual_protocol": self.surface.visual_protocol,
            "input": self.surface.input_name,
            "output": self.surface.output_name,
            "selected": (
                _identity_payload(self._selected_agent)
                if self._selected_agent is not None
                else None
            ),
            "overflow_count": sum(session.slot is None for session in sessions),
            "activity_motion": self.activity_motion,
            "session_ttl": self.session_ttl,
            "sessions": [
                {
                    **_identity_payload(session.identity),
                    "state": session.state.value,
                    "slot": session.slot,
                    "accent": session.accent,
                    "selected": session.identity == self._selected_agent,
                    "leased": self._has_live_lease(session.identity),
                    "label": _session_label(session),
                    "metadata": dict(session.metadata),
                }
                for session in sessions
            ],
        }

    def select_slot(self, slot: int) -> bool:
        if not 0 <= slot < len(self._slots):
            return False
        identity = self._slots[slot]
        if identity is None:
            return False
        self._selected_agent = identity
        self._sequence += 1
        session = self._sessions[identity]
        session.last_seen = self._sequence
        session.last_activity_at = time.monotonic()
        self._render_dirty = True
        return True

    def _ensure_session(self, identity: AgentIdentity) -> AgentSession:
        session = self._sessions.get(identity)
        if session is not None:
            return session
        self._sequence += 1
        session = AgentSession(
            identity=identity,
            last_seen=self._sequence,
            last_activity_at=time.monotonic(),
        )
        self._sessions[identity] = session
        self._assign_slot(session)
        if self._selected_agent is None and len(self._sessions) == 1:
            self._selected_agent = identity
        self._render_dirty = True
        return session

    def _register_lease(self, client: Client, message: dict[str, Any]) -> None:
        lease_id = parse_identifier(message.get("lease_id"), field="lease_id")
        assert lease_id is not None
        metadata = parse_metadata(message.get("metadata"))

        if client.lease_id is not None and client.lease_id != lease_id:
            self._release_lease(client)
        previous_client = self._lease_clients.get(lease_id)
        if previous_client is not None and previous_client is not client:
            previous_client.lease_id = None
        client.lease_id = lease_id
        self._lease_clients[lease_id] = client
        self._lease_metadata[lease_id] = metadata

        identity = (
            parse_agent(message.get("agent"), default=None)
            if message.get("agent")
            else None
        )
        if identity is not None:
            self._bind_lease(lease_id, identity, metadata)
        else:
            identity = self._lease_agents.get(lease_id)
            if identity is not None and metadata:
                self.update_agent(
                    identity,
                    self._sessions[identity].state,
                    metadata=metadata,
                )

        payload: dict[str, Any] = {
            "type": "session_lease_ack",
            "lease_id": lease_id,
        }
        if identity is not None and identity in self._sessions:
            payload["session"] = self._state_ack(self._sessions[identity])
        self._send(client, payload)

    def _bind_lease(
        self,
        lease_id: str,
        identity: AgentIdentity,
        metadata: dict[str, str] | None = None,
    ) -> None:
        previous_identity = self._lease_agents.get(lease_id)
        self._lease_agents[lease_id] = identity
        combined_metadata = dict(self._lease_metadata.get(lease_id, {}))
        if metadata:
            combined_metadata.update(metadata)
        session = self._ensure_session(identity)
        if combined_metadata:
            session.metadata.update(combined_metadata)

        if previous_identity is not None and previous_identity != identity:
            if not self._has_live_lease(previous_identity):
                self.end_agent(previous_identity)

        lease_client = self._lease_clients.get(lease_id)
        if lease_client is not None:
            self._send(
                lease_client,
                {
                    "type": "session_lease_bound",
                    "lease_id": lease_id,
                    "session": self._state_ack(session),
                },
            )

    def _release_lease(self, client: Client) -> None:
        lease_id = client.lease_id
        if lease_id is None:
            return
        client.lease_id = None
        if self._lease_clients.get(lease_id) is not client:
            return
        del self._lease_clients[lease_id]
        identity = self._lease_agents.pop(lease_id, None)
        self._lease_metadata.pop(lease_id, None)
        if identity is not None and not self._has_live_lease(identity):
            self.end_agent(identity)

    def _has_live_lease(self, identity: AgentIdentity) -> bool:
        return any(
            agent == identity and lease_id in self._lease_clients
            for lease_id, agent in self._lease_agents.items()
        )

    def _has_pending_approval(self, identity: AgentIdentity) -> bool:
        approval_actions = {ControlAction.APPROVE, ControlAction.REJECT}
        return any(
            client.agent == identity
            and client.request_id is not None
            and bool(client.actions & approval_actions)
            for client in self._clients.values()
        )

    def _state_ack(self, session: AgentSession) -> dict[str, Any]:
        return {
            "type": "state_ack",
            **_identity_payload(session.identity),
            "state": session.state.value,
            "slot": session.slot,
            "scene": session.slot + 1 if session.slot is not None else None,
            "accent": session.accent,
            "selected": session.identity == self._selected_agent,
            "leased": self._has_live_lease(session.identity),
            "label": _session_label(session),
        }

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
        self._assign_accent(session)

    def _assign_accent(self, session: AgentSession) -> None:
        if session.slot is None:
            return
        used = {
            candidate.accent
            for candidate in self._sessions.values()
            if candidate is not session
            and candidate.slot is not None
            and candidate.accent is not None
        }
        preferred = session.accent
        if preferred is None and self.identity_store is not None:
            preferred = self.identity_store.preferred_accent(session.identity)
        if preferred not in self.surface.accent_names or preferred in used:
            preferred = next(
                (name for name in self.surface.accent_names if name not in used),
                None,
            )
        session.accent = preferred
        if preferred is not None and self.identity_store is not None:
            try:
                self.identity_store.remember(session.identity, preferred)
            except OSError:
                pass

    def _fill_empty_slots(self) -> None:
        waiting = sorted(
            (session for session in self._sessions.values() if session.slot is None),
            key=lambda session: (
                session.state is AgentState.WAITING_FOR_APPROVAL,
                session.last_seen,
            ),
            reverse=True,
        )
        for session in waiting:
            if None not in self._slots:
                break
            self._assign_slot(session)

    def _open_server(self) -> socket.socket:
        if os.path.lexists(self.socket_path):
            mode = os.lstat(self.socket_path).st_mode
            if not stat.S_ISSOCK(mode):
                raise OSError(
                    errno.EEXIST,
                    "socket path exists and is not a Unix socket",
                    self.socket_path,
                )
            probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                probe.connect(self.socket_path)
            except ConnectionRefusedError:
                os.unlink(self.socket_path)
            except FileNotFoundError:
                pass
            else:
                raise OSError(
                    errno.EADDRINUSE,
                    "another Pad-Lattice daemon is already running",
                    self.socket_path,
                )
            finally:
                probe.close()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server.bind(self.socket_path)
            self._owns_socket_path = True
            server.listen()
            server.setblocking(False)
        except BaseException:
            server.close()
            if self._owns_socket_path:
                try:
                    os.unlink(self.socket_path)
                except FileNotFoundError:
                    pass
                self._owns_socket_path = False
            raise
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
        if identity is None or action not in self._available_actions():
            return
        recipients = sorted(
            (
                client
                for client in self._clients.values()
                if client.agent == identity and action in client.actions
            ),
            key=lambda client: (
                client.request_id is None,
                client.subscribed_at,
            ),
        )
        if not recipients:
            return

        now = time.monotonic()
        debounce_key = (identity, action)
        last_action_at = self._last_action_at.get(debounce_key)
        if last_action_at is not None and now - last_action_at < self.action_debounce:
            return
        self._last_action_at[debounce_key] = now
        session = self._sessions.get(identity)
        if session is not None:
            self._sequence += 1
            session.last_seen = self._sequence
            session.last_activity_at = now

        recipient = recipients[0]
        request_id = recipient.request_id
        if recipient.one_shot:
            recipient.actions = frozenset()
            recipient.request_id = None
            recipient.one_shot = False
            self._render_dirty = True
        self._send(
            recipient,
            action_message(action, identity, request_id=request_id),
        )

    def _render_if_needed(self) -> None:
        now = time.monotonic()
        self._expire_sessions(now)
        for session in self._sessions.values():
            if session.terminal_state_until is not None and now >= session.terminal_state_until:
                session.state = AgentState.WAITING_FOR_REPLY
                session.terminal_state_until = None
                self._render_dirty = True

        refresh_running = (
            self.activity_motion
            and self.state is AgentState.RUNNING
            and now >= self._next_activity_render
        )
        if not self._render_dirty and not refresh_running:
            return

        self.surface.render(self._surface_view())
        self._frame += 1
        self._render_dirty = False
        self._next_activity_render = now + RUNNING_ACTIVITY_INTERVAL

    def _expire_sessions(self, now: float) -> None:
        if self.session_ttl == 0:
            return
        expired = [
            session.identity
            for session in self._sessions.values()
            if not self._has_live_lease(session.identity)
            and now - session.last_activity_at >= self.session_ttl
        ]
        for identity in expired:
            self.end_agent(identity)

    def _surface_view(self) -> SurfaceView:
        indicators = tuple(
            SessionIndicator(
                slot=session.slot,
                state=session.state,
                selected=session.identity == self._selected_agent,
                accent=session.accent or self.surface.accent_names[session.slot],
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
            overflow_count=sum(
                session.slot is None for session in self._sessions.values()
            ),
            activity_motion=self.activity_motion,
        )

    def _available_actions(self) -> frozenset[ControlAction]:
        identity = self._selected_agent
        session = self.selected_session
        if identity is None or session is None:
            return frozenset()
        return frozenset(
            action
            for client in self._clients.values()
            if client.agent == identity
            for action in client.actions
            if session.state in ACTION_STATES[action]
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
        self._release_lease(client)
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


def _identity_payload(identity: AgentIdentity) -> dict[str, str]:
    return {"backend": identity.backend, "session_id": identity.session_id}


def _session_label(session: AgentSession) -> str:
    if label := session.metadata.get("label"):
        return label
    if cwd := session.metadata.get("cwd"):
        name = os.path.basename(os.path.normpath(cwd))
        if name:
            return name
    return session.identity.session_id[:8]
