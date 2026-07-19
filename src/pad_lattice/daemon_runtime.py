"""Unix-socket and surface runtime for the Pad-Lattice control plane."""

from __future__ import annotations

import errno
import os
import selectors
import socket
import stat
import struct
import time
from dataclasses import dataclass, field
from typing import Any

from pad_lattice.audio import AudioFeedback, Earcon
from pad_lattice.control_plane import (
    DEFAULT_SESSION_TTL,
    AgentSession,
    ControlPlane,
    ControlPlaneError,
)
from pad_lattice.devices.base import (
    ActionPressed,
    ControlSurface,
    ExperienceRequested,
    ExperienceStopRequested,
    SessionSelected,
    SurfaceEvent,
    SurfaceView,
)
from pad_lattice.devices.composite import surface_descriptors
from pad_lattice.events import AgentIdentity, AgentState, ControlAction
from pad_lattice.experience_runtime import ExperienceController
from pad_lattice.identity_store import IdentityStore
from pad_lattice.protocol import (
    MAX_MESSAGE_BYTES,
    PingCommand,
    PreviewCommand,
    PreviewEndCommand,
    ProtocolError,
    SessionEndCommand,
    SessionLeaseCommand,
    StateCommand,
    StatusCommand,
    SubscribeActionsCommand,
    action_message,
    decode_message,
    encode_message,
    error_message,
    parse_client_command,
    wire_message,
)
from pad_lattice.visual_protocol import RUNNING_ACTIVITY_INTERVAL


STATE_EARCONS = {
    AgentState.WAITING_FOR_REPLY: Earcon.QUESTION,
    AgentState.WAITING_FOR_APPROVAL: Earcon.APPROVAL,
    AgentState.SUCCESS: Earcon.SUCCESS,
    AgentState.ERROR: Earcon.ERROR,
    AgentState.CANCELLED: Earcon.CANCELLED,
}
ACTION_EARCONS = {
    ControlAction.APPROVE: Earcon.APPROVE,
    ControlAction.REJECT: Earcon.REJECT,
    ControlAction.RETRY: Earcon.RETRY,
    ControlAction.STOP: Earcon.STOP,
}


@dataclass
class Client:
    socket: socket.socket
    buffer: bytearray = field(default_factory=bytearray)
    output_buffer: bytearray = field(default_factory=bytearray)
    close_after_write: bool = False

    @property
    def client_id(self) -> int:
        return self.socket.fileno()


class PadLatticeDaemon:
    """Adapt Unix-socket commands and surface events to the control plane."""

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
        audio_feedback: AudioFeedback | None = None,
    ) -> None:
        self.surface = surface
        self.socket_path = socket_path
        self.poll_interval = poll_interval
        self.activity_motion = activity_motion
        self.audio_feedback = audio_feedback
        self.control = ControlPlane(
            surface.selector_capacity,
            surface.accent_names,
            terminal_hold=terminal_hold,
            action_debounce=action_debounce,
            session_ttl=session_ttl,
            identity_store=identity_store,
        )
        self.experience = ExperienceController(
            surface,
            audio_feedback=audio_feedback,
        )
        self._selector = selectors.DefaultSelector()
        self._server: socket.socket | None = None
        self._owns_socket_path = False
        self._clients: dict[int, Client] = {}
        self._frame = 0
        self._rendered_revision = -1
        self._next_activity_render = 0.0
        self._announced_states: dict[AgentIdentity, AgentState] = {}
        self._closed = False

    def run(self) -> None:
        try:
            self._server = self._open_server()
            self._selector.register(
                self._server,
                selectors.EVENT_READ,
                self._accept_client,
            )
            self.surface.initialize()
            while True:
                self._render_if_needed()
                for key, mask in self._selector.select(timeout=self.poll_interval):
                    callback = key.data
                    callback(key.fileobj, mask)
                for event in self.surface.poll_events():
                    self._handle_surface_event(event)
        finally:
            self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.experience.stop(reason="daemon_stopped")
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
        try:
            if self.audio_feedback is not None:
                self.audio_feedback.close()
        finally:
            self.surface.close()

    def handle_message(self, client: Client, message: dict[str, Any]) -> None:
        command = parse_client_command(message)
        now = time.monotonic()
        try:
            if isinstance(command, StateCommand):
                if command.lease_id is not None:
                    session, owner_id = self.control.bind_lease(
                        command.lease_id,
                        command.agent,
                        command.metadata,
                        now=now,
                    )
                    if owner_id is not None:
                        self._send_to_client_id(
                            owner_id,
                            wire_message(
                                "session_lease_bound",
                                lease_id=command.lease_id,
                                session=self._state_ack(session),
                            ),
                        )
                session = self.control.update_agent(
                    command.agent,
                    command.state,
                    metadata=command.metadata,
                    now=now,
                )
                self._preempt_experience_if_needed()
                self._announce_state(session)
                if command.reply:
                    self._send(client, self._state_ack(session))
                return
            if isinstance(command, SessionLeaseCommand):
                session = self.control.register_lease(
                    client.client_id,
                    command.lease_id,
                    agent=command.agent,
                    metadata=command.metadata,
                    now=now,
                )
                payload = wire_message(
                    "session_lease_ack",
                    lease_id=command.lease_id,
                )
                if session is not None:
                    payload["session"] = self._state_ack(session)
                self._send(client, payload)
                return
            if isinstance(command, SubscribeActionsCommand):
                self.control.subscribe(
                    client.client_id,
                    command.agent,
                    command.actions,
                    request_id=command.request_id,
                    one_shot=command.one_shot,
                    now=now,
                )
                return
            if isinstance(command, PreviewCommand):
                self.control.set_preview(
                    client.client_id,
                    command.preview_id,
                    command.state,
                    expires_at=now + command.ttl,
                )
                self._send(
                    client,
                    wire_message(
                        "preview_ack",
                        preview_id=command.preview_id,
                        state=command.state.value,
                    ),
                )
                return
            if isinstance(command, PreviewEndCommand):
                self.control.end_preview(client.client_id, command.preview_id)
                self._send(
                    client,
                    wire_message(
                        "preview_end_ack",
                        preview_id=command.preview_id,
                    ),
                )
                return
            if isinstance(command, SessionEndCommand):
                self.control.end_agent(command.agent)
                self._announced_states.pop(command.agent, None)
                return
            if isinstance(command, StatusCommand):
                self._send(client, self.status_snapshot())
                return
            if isinstance(command, PingCommand):
                self._send(client, wire_message("pong"))
                return
        except ControlPlaneError as exc:
            raise ProtocolError(str(exc), code=exc.code) from exc
        raise AssertionError(f"unhandled protocol command: {command!r}")

    def status_snapshot(self) -> dict[str, Any]:
        sessions = sorted(
            self.control.sessions,
            key=lambda session: (
                session.slot is None,
                session.slot if session.slot is not None else session.last_seen,
            ),
        )
        return wire_message(
            "status",
            profile=self.surface.profile_id,
            visual_protocol=self.surface.visual_protocol,
            input=self.surface.input_name,
            output=self.surface.output_name,
            surfaces=list(surface_descriptors(self.surface)),
            selected=(
                _identity_payload(self.control.selected_agent)
                if self.control.selected_agent is not None
                else None
            ),
            overflow_count=self.control.overflow_count,
            activity_motion=self.activity_motion,
            audio_feedback=self.audio_feedback is not None,
            experience=self.experience.kind,
            preview_active=self.control.preview is not None,
            session_ttl=self.control.session_ttl,
            sessions=[
                {
                    **_identity_payload(session.identity),
                    "state": session.state.value,
                    "slot": session.slot,
                    "accent": session.accent,
                    "selected": session.identity == self.control.selected_agent,
                    "leased": self.control.is_leased(session.identity),
                    "label": self.control.session_label(session),
                    "metadata": dict(session.metadata),
                }
                for session in sessions
            ],
        )

    def _state_ack(self, session: AgentSession) -> dict[str, Any]:
        return wire_message(
            "state_ack",
            **_identity_payload(session.identity),
            state=session.state.value,
            slot=session.slot,
            scene=session.slot + 1 if session.slot is not None else None,
            accent=session.accent,
            selected=session.identity == self.control.selected_agent,
            leased=self.control.is_leased(session.identity),
            label=self.control.session_label(session),
        )

    def _available_actions(self) -> frozenset[ControlAction]:
        return self.control.available_actions()

    def _surface_view(self) -> SurfaceView:
        return self.control.surface_view(
            frame=self._frame,
            activity_motion=self.activity_motion,
        )

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
            os.chmod(self.socket_path, 0o600)
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

    def _accept_client(self, server: socket.socket, mask: int) -> None:
        client_socket, _ = server.accept()
        if not _peer_is_current_user(client_socket):
            client_socket.close()
            return
        client_socket.setblocking(False)
        client = Client(client_socket)
        self._clients[client.client_id] = client
        self._selector.register(
            client_socket,
            selectors.EVENT_READ,
            self._service_client,
        )

    def _service_client(self, client_socket: socket.socket, mask: int) -> None:
        client = self._clients.get(client_socket.fileno())
        if client is None:
            return
        if mask & selectors.EVENT_READ and not client.close_after_write:
            self._read_client(client_socket)
        client = self._clients.get(client_socket.fileno())
        if mask & selectors.EVENT_WRITE and client is not None:
            self._flush_client(client)

    def _read_client(self, client_socket: socket.socket) -> None:
        client = self._clients[client_socket.fileno()]
        try:
            data = client_socket.recv(4096)
        except (BlockingIOError, InterruptedError):
            return
        if not data:
            self._close_client(client)
            return
        client.buffer += data
        if len(client.buffer) > MAX_MESSAGE_BYTES and b"\n" not in client.buffer:
            client.close_after_write = True
            self._send(
                client,
                error_message(
                    ProtocolError(
                        "protocol message exceeds the size limit",
                        code="frame_too_large",
                    )
                ),
            )
            return
        while b"\n" in client.buffer:
            line, client.buffer = client.buffer.split(b"\n", 1)
            if not line.strip():
                continue
            try:
                self.handle_message(client, decode_message(line))
            except ProtocolError as exc:
                self._send(client, error_message(exc))

    def _handle_surface_event(self, event: SurfaceEvent) -> None:
        now = time.monotonic()
        if isinstance(event, ExperienceRequested):
            if self._agent_attention_required():
                self.experience.block(
                    event.kind,
                    "An agent is waiting for approval or a reply.",
                )
                return
            self.experience.start(
                event.kind,
                now=now,
                host_show_audio=self.audio_feedback is not None,
            )
            return
        if isinstance(event, ExperienceStopRequested):
            if self.experience.stop():
                self._rendered_revision = -1
            return
        if self.experience.active:
            self.experience.handle_event(event, now=now)
            return
        if isinstance(event, SessionSelected):
            if self.control.select_slot(event.slot, now=now):
                self._play_audio(Earcon.SESSION_SELECTED, slot=event.slot)
        elif isinstance(event, ActionPressed):
            self._handle_action(event.action)

    def _handle_action(self, action: ControlAction) -> None:
        dispatch = self.control.dispatch_action(action, now=time.monotonic())
        if dispatch is None:
            selected = self.control.selected_session
            self._play_audio(
                Earcon.UNAVAILABLE,
                slot=selected.slot if selected is not None else None,
            )
            return
        selected = self.control.selected_session
        self._play_audio(
            ACTION_EARCONS[action],
            slot=selected.slot if selected is not None else None,
        )
        client = self._clients.get(dispatch.client_id)
        if client is None:
            return
        self._send(
            client,
            action_message(
                dispatch.action,
                dispatch.agent,
                request_id=dispatch.request_id,
            ),
        )

    def _render_if_needed(self) -> None:
        now = time.monotonic()
        self.control.tick(now=now)
        self._preempt_experience_if_needed()
        if self.experience.active:
            if self.experience.tick(now=now):
                self._rendered_revision = -1
            else:
                return
        refresh_running = (
            self.control.preview is None
            and self.activity_motion
            and self.control.state is AgentState.RUNNING
            and now >= self._next_activity_render
        )
        if self._rendered_revision == self.control.revision and not refresh_running:
            return

        self.surface.render(self._surface_view())
        self._frame += 1
        self._rendered_revision = self.control.revision
        self._next_activity_render = now + RUNNING_ACTIVITY_INTERVAL

    def _agent_attention_required(self) -> bool:
        return any(
            session.state
            in {AgentState.WAITING_FOR_REPLY, AgentState.WAITING_FOR_APPROVAL}
            for session in self.control.sessions
        )

    def _preempt_experience_if_needed(self) -> None:
        if self.experience.active and self._agent_attention_required():
            self.experience.stop(reason="agent_attention_required")
            self._rendered_revision = -1

    def _announce_state(self, session: AgentSession) -> None:
        previous = self._announced_states.get(session.identity)
        self._announced_states[session.identity] = session.state
        cue = STATE_EARCONS.get(session.state)
        if cue is not None and previous is not session.state:
            self._play_audio(cue, slot=session.slot)

    def _play_audio(self, cue: Earcon, *, slot: int | None) -> None:
        if self.audio_feedback is None:
            return
        try:
            self.audio_feedback.play(cue, slot=slot)
        except OSError:
            pass

    def _send_to_client_id(self, client_id: int, message: dict[str, Any]) -> None:
        client = self._clients.get(client_id)
        if client is not None:
            self._send(client, message)

    def _send(self, client: Client, message: dict[str, Any]) -> None:
        client.output_buffer.extend(encode_message(message))
        self._flush_client(client)

    def _flush_client(self, client: Client) -> None:
        if not client.output_buffer:
            if client.close_after_write:
                self._close_client(client)
            else:
                self._update_client_interest(client)
            return
        try:
            sent = client.socket.send(client.output_buffer)
        except (BlockingIOError, InterruptedError):
            sent = 0
        except OSError:
            self._close_client(client)
            return
        if sent:
            del client.output_buffer[:sent]
        if not client.output_buffer and client.close_after_write:
            self._close_client(client)
            return
        self._update_client_interest(client)

    def _update_client_interest(self, client: Client) -> None:
        if client.client_id not in self._clients:
            return
        events = 0 if client.close_after_write else selectors.EVENT_READ
        if client.output_buffer:
            events |= selectors.EVENT_WRITE
        try:
            self._selector.modify(client.socket, events, self._service_client)
        except KeyError:
            pass

    def _close_client(self, client: Client) -> None:
        client_id = client.client_id
        self._clients.pop(client_id, None)
        self.control.disconnect(client_id)
        active_identities = {session.identity for session in self.control.sessions}
        for identity in tuple(self._announced_states):
            if identity not in active_identities:
                self._announced_states.pop(identity, None)
        client.output_buffer.clear()
        try:
            self._selector.unregister(client.socket)
        except Exception:
            pass
        client.socket.close()


def _identity_payload(identity: AgentIdentity) -> dict[str, str]:
    return {"backend": identity.backend, "session_id": identity.session_id}


def _peer_is_current_user(client: socket.socket) -> bool:
    """Reject cross-user Unix-socket clients where peer credentials exist."""

    peer_credential_option = getattr(socket, "SO_PEERCRED", None)
    if peer_credential_option is None:
        return True
    credential_size = struct.calcsize("3i")
    try:
        credentials = client.getsockopt(
            socket.SOL_SOCKET,
            peer_credential_option,
            credential_size,
        )
        _, peer_uid, _ = struct.unpack("3i", credentials)
    except (OSError, struct.error):
        return False
    return peer_uid == os.geteuid()
