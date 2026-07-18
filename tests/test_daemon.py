from __future__ import annotations

import errno
import stat
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from pad_lattice.audio import Earcon
from pad_lattice.daemon_runtime import Client, PadLatticeDaemon
from pad_lattice.devices.base import SessionSelected
from pad_lattice.events import AgentIdentity, AgentState, ControlAction
from pad_lattice.identity_store import IdentityStore
from pad_lattice.protocol import (
    MAX_MESSAGE_BYTES,
    WIRE_PROTOCOL_VERSION,
    decode_message,
    wire_message,
)


def wire(message):
    return {"protocol": WIRE_PROTOCOL_VERSION, **message}


class FakeSocket:
    _next_fileno = 100

    def __init__(self) -> None:
        self.sent = b""
        self._fileno = self._next_fileno
        FakeSocket._next_fileno += 1

    def sendall(self, data: bytes) -> None:
        self.sent += data

    def send(self, data: bytes) -> int:
        self.sent += bytes(data)
        return len(data)

    def fileno(self) -> int:
        return self._fileno

    def close(self) -> None:
        pass


class FakeSurface:
    profile_id = "test/grid/device"
    input_name = "Test input"
    output_name = "Test output"
    selector_capacity = 4
    accent_names = ("cyan", "magenta", "lime", "orange")
    visual_protocol = 1

    def __init__(self) -> None:
        self.views = []
        self.events = []
        self.initialized = False
        self.closed = False

    def initialize(self) -> None:
        self.initialized = True

    def render(self, view) -> None:
        self.views.append(view)

    def poll_events(self):
        events, self.events = self.events, []
        return events

    def close(self) -> None:
        self.closed = True


class FakeAudioFeedback:
    def __init__(self) -> None:
        self.events = []
        self.closed = False

    def play(self, cue, *, slot=None) -> None:
        self.events.append((cue, slot))

    def close(self) -> None:
        self.closed = True


class DaemonTest(TestCase):
    def setUp(self) -> None:
        self.daemons = []

    def tearDown(self) -> None:
        for daemon in self.daemons:
            daemon.close()

    def daemon(self, **kwargs) -> PadLatticeDaemon:
        daemon = PadLatticeDaemon(
            FakeSurface(),
            "/tmp/pad-lattice-unit-test.sock",
            **kwargs,
        )
        self.daemons.append(daemon)
        return daemon

    def add_client(
        self,
        daemon: PadLatticeDaemon,
        identity: AgentIdentity,
        *actions: ControlAction,
    ) -> Client:
        client = Client(FakeSocket())
        daemon._clients[client.socket.fileno()] = client
        daemon.handle_message(
            client,
            wire(
                {
                    "type": "subscribe_actions",
                    "agent": {
                        "backend": identity.backend,
                        "session_id": identity.session_id,
                    },
                    "actions": [action.value for action in actions],
                }
            ),
        )
        return client

    def update_agent(
        self,
        daemon: PadLatticeDaemon,
        identity: AgentIdentity,
        state: AgentState,
        *,
        metadata: dict[str, str] | None = None,
    ) -> None:
        daemon.control.update_agent(
            identity,
            state,
            metadata=metadata,
            now=time.monotonic(),
        )

    def test_state_message_registers_agent_identity(self) -> None:
        daemon = self.daemon()
        client = Client(FakeSocket())

        daemon.handle_message(
            client,
            wire({
                "type": "state",
                "state": "running",
                "agent": {"backend": "codex", "session_id": "session-1"},
            }),
        )

        self.assertEqual(daemon.control.selected_agent, AgentIdentity("codex", "session-1"))
        self.assertIs(daemon.control.state, AgentState.RUNNING)

    def test_audio_announces_semantic_state_changes_but_not_running(self) -> None:
        audio = FakeAudioFeedback()
        daemon = self.daemon(audio_feedback=audio)
        client = Client(FakeSocket())
        identity = {"backend": "codex", "session_id": "session-1"}

        for state in (
            "running",
            "waiting_for_reply",
            "waiting_for_reply",
            "waiting_for_approval",
            "success",
        ):
            daemon.handle_message(
                client,
                wire({"type": "state", "state": state, "agent": identity}),
            )

        self.assertEqual(
            audio.events,
            [
                (Earcon.QUESTION, 0),
                (Earcon.APPROVAL, 0),
                (Earcon.SUCCESS, 0),
            ],
        )

    def test_subscribe_message_records_target_and_capabilities(self) -> None:
        daemon = self.daemon()
        client = Client(FakeSocket())

        daemon.handle_message(
            client,
            wire({
                "type": "subscribe_actions",
                "agent": {"backend": "codex", "session_id": "session-1"},
                "actions": ["approve", "reject"],
            }),
        )

        subscription = daemon.control._subscriptions[client.client_id]
        self.assertEqual(
            subscription.agent,
            AgentIdentity("codex", "session-1"),
        )
        self.assertEqual(
            subscription.actions,
            frozenset({ControlAction.APPROVE, ControlAction.REJECT}),
        )

    def test_request_scoped_action_is_delivered_once_to_oldest_waiter(self) -> None:
        daemon = self.daemon()
        identity = AgentIdentity("codex", "session-1")
        self.update_agent(daemon, identity, AgentState.WAITING_FOR_APPROVAL)
        first = Client(FakeSocket())
        second = Client(FakeSocket())
        for client, request_id in ((first, "first"), (second, "second")):
            daemon._clients[client.socket.fileno()] = client
            daemon.handle_message(
                client,
                wire({
                    "type": "subscribe_actions",
                    "agent": {"backend": "codex", "session_id": "session-1"},
                    "actions": ["approve", "reject"],
                    "request_id": request_id,
                    "one_shot": True,
                }),
            )

        daemon._handle_action(ControlAction.APPROVE)

        self.assertIn(b'"request_id":"first"', first.socket.sent)
        self.assertEqual(second.socket.sent, b"")
        self.assertFalse(
            daemon.control._subscriptions[first.client_id].actions
        )
        self.assertEqual(
            daemon._available_actions(),
            frozenset({ControlAction.APPROVE, ControlAction.REJECT}),
        )

    def test_overlapping_approvals_remain_available_until_each_is_decided(self) -> None:
        daemon = self.daemon(action_debounce=0)
        identity = AgentIdentity("codex", "session-1")
        self.update_agent(daemon, identity, AgentState.WAITING_FOR_APPROVAL)
        clients = [Client(FakeSocket()), Client(FakeSocket())]
        for index, client in enumerate(clients):
            daemon._clients[client.socket.fileno()] = client
            daemon.handle_message(
                client,
                wire({
                    "type": "subscribe_actions",
                    "agent": {"backend": "codex", "session_id": "session-1"},
                    "actions": ["approve", "reject"],
                    "request_id": f"request-{index}",
                    "one_shot": True,
                }),
            )

        daemon._handle_action(ControlAction.APPROVE)
        self.update_agent(daemon, identity, AgentState.RUNNING)

        self.assertIs(daemon.control.state, AgentState.WAITING_FOR_APPROVAL)
        self.assertEqual(
            daemon._available_actions(),
            frozenset({ControlAction.APPROVE, ControlAction.REJECT}),
        )

        daemon._handle_action(ControlAction.REJECT)
        self.update_agent(daemon, identity, AgentState.RUNNING)

        self.assertIs(daemon.control.state, AgentState.RUNNING)
        self.assertIn(b'"request_id":"request-0"', clients[0].socket.sent)
        self.assertIn(b'"request_id":"request-1"', clients[1].socket.sent)

    def test_lease_disconnect_removes_bound_session_immediately(self) -> None:
        daemon = self.daemon()
        lease_client = Client(FakeSocket())
        daemon._clients[lease_client.socket.fileno()] = lease_client
        daemon.handle_message(
            lease_client,
            wire({
                "type": "session_lease",
                "lease_id": "lease-1",
                "metadata": {"label": "docs"},
            }),
        )
        state_client = Client(FakeSocket())
        daemon.handle_message(
            state_client,
            wire({
                "type": "state",
                "state": "running",
                "lease_id": "lease-1",
                "reply": True,
                "agent": {
                    "backend": "codex",
                    "session_id": "session-1",
                    "cwd": "/work/project",
                },
            }),
        )

        status = daemon.status_snapshot()["sessions"][0]
        self.assertTrue(status["leased"])
        self.assertEqual(status["label"], "docs")
        self.assertIn(b'"type":"state_ack"', state_client.socket.sent)

        daemon._close_client(lease_client)

        self.assertEqual(daemon.control.sessions, ())
        self.assertIsNone(daemon.control.selected_agent)

    def test_replacing_a_lease_connection_ignores_the_old_disconnect(self) -> None:
        daemon = self.daemon()
        identity = AgentIdentity("codex", "session-1")
        first = Client(FakeSocket())
        second = Client(FakeSocket())
        for client in (first, second):
            daemon._clients[client.socket.fileno()] = client
            daemon.handle_message(
                client,
                wire({
                    "type": "session_lease",
                    "lease_id": "lease-1",
                    "agent": {"backend": "codex", "session_id": "session-1"},
                }),
            )

        daemon._close_client(first)

        self.assertIn(identity, daemon.control._sessions)
        self.assertTrue(daemon.control.is_leased(identity))

        daemon._close_client(second)
        self.assertNotIn(identity, daemon.control._sessions)

    def test_background_update_does_not_steal_selection(self) -> None:
        daemon = self.daemon()
        first = AgentIdentity("codex", "first")
        second = AgentIdentity("codex", "second")

        self.update_agent(daemon, first, AgentState.WAITING_FOR_REPLY)
        self.update_agent(daemon, second, AgentState.RUNNING)

        self.assertEqual(daemon.control.selected_agent, first)
        self.assertIs(daemon.control.state, AgentState.WAITING_FOR_REPLY)

    def test_selector_changes_the_active_session(self) -> None:
        daemon = self.daemon()
        first = AgentIdentity("codex", "first")
        second = AgentIdentity("codex", "second")
        self.update_agent(daemon, first, AgentState.WAITING_FOR_REPLY)
        self.update_agent(daemon, second, AgentState.RUNNING)
        second_slot = daemon.control._sessions[second].slot
        assert second_slot is not None

        daemon._handle_surface_event(SessionSelected(second_slot))

        self.assertEqual(daemon.control.selected_agent, second)
        self.assertIs(daemon.control.state, AgentState.RUNNING)

    def test_selector_plays_session_specific_confirmation(self) -> None:
        audio = FakeAudioFeedback()
        daemon = self.daemon(audio_feedback=audio)
        first = AgentIdentity("codex", "first")
        second = AgentIdentity("codex", "second")
        self.update_agent(daemon, first, AgentState.RUNNING)
        self.update_agent(daemon, second, AgentState.RUNNING)
        second_slot = daemon.control._sessions[second].slot
        assert second_slot is not None

        daemon._handle_surface_event(SessionSelected(second_slot))

        self.assertEqual(
            audio.events,
            [(Earcon.SESSION_SELECTED, second_slot)],
        )

    def test_action_is_sent_only_to_selected_matching_subscriber(self) -> None:
        daemon = self.daemon()
        first = AgentIdentity("codex", "first")
        second = AgentIdentity("codex", "second")
        self.update_agent(daemon, first, AgentState.WAITING_FOR_APPROVAL)
        self.update_agent(daemon, second, AgentState.WAITING_FOR_APPROVAL)
        first_client = self.add_client(daemon, first, ControlAction.APPROVE)
        second_client = self.add_client(daemon, second, ControlAction.APPROVE)

        daemon._handle_action(ControlAction.APPROVE)

        self.assertIn(b'"action":"approve"', first_client.socket.sent)
        self.assertIn(b'"session_id":"first"', first_client.socket.sent)
        self.assertEqual(second_client.socket.sent, b"")

    def test_unavailable_action_is_not_emitted(self) -> None:
        daemon = self.daemon()
        identity = AgentIdentity("codex", "session")
        self.update_agent(daemon, identity, AgentState.WAITING_FOR_APPROVAL)
        client = self.add_client(daemon, identity, ControlAction.REJECT)

        daemon._handle_action(ControlAction.APPROVE)

        self.assertEqual(client.socket.sent, b"")

    def test_audio_confirms_dispatched_and_unavailable_actions(self) -> None:
        audio = FakeAudioFeedback()
        daemon = self.daemon(audio_feedback=audio, action_debounce=0)
        identity = AgentIdentity("codex", "session")
        self.update_agent(daemon, identity, AgentState.WAITING_FOR_APPROVAL)
        self.add_client(daemon, identity, ControlAction.APPROVE)

        daemon._handle_action(ControlAction.APPROVE)
        daemon._handle_action(ControlAction.REJECT)

        self.assertEqual(
            audio.events,
            [(Earcon.APPROVE, 0), (Earcon.UNAVAILABLE, 0)],
        )

    def test_handle_action_debounces_repeated_actions(self) -> None:
        daemon = self.daemon(action_debounce=60.0)
        identity = AgentIdentity("codex", "session")
        self.update_agent(daemon, identity, AgentState.RUNNING)
        client = self.add_client(daemon, identity, ControlAction.STOP)

        daemon._handle_action(ControlAction.STOP)
        daemon._handle_action(ControlAction.STOP)

        self.assertEqual(client.socket.sent.count(b'"action":"stop"'), 1)

    def test_first_action_is_allowed_when_monotonic_is_low(self) -> None:
        daemon = self.daemon(action_debounce=60.0)
        identity = AgentIdentity("codex", "session")
        self.update_agent(daemon, identity, AgentState.RUNNING)
        client = self.add_client(daemon, identity, ControlAction.STOP)

        with patch("pad_lattice.daemon_runtime.time.monotonic", return_value=1.0):
            daemon._handle_action(ControlAction.STOP)

        self.assertEqual(client.socket.sent.count(b'"action":"stop"'), 1)

    def test_debounce_is_scoped_to_agent_identity(self) -> None:
        daemon = self.daemon(action_debounce=60.0)
        first = AgentIdentity("codex", "first")
        second = AgentIdentity("codex", "second")
        self.update_agent(daemon, first, AgentState.RUNNING)
        self.update_agent(daemon, second, AgentState.RUNNING)
        first_client = self.add_client(daemon, first, ControlAction.STOP)
        second_client = self.add_client(daemon, second, ControlAction.STOP)

        daemon._handle_action(ControlAction.STOP)
        second_slot = daemon.control._sessions[second].slot
        assert second_slot is not None
        daemon.control.select_slot(second_slot, now=time.monotonic())
        daemon._handle_action(ControlAction.STOP)

        self.assertEqual(first_client.socket.sent.count(b'"action":"stop"'), 1)
        self.assertEqual(second_client.socket.sent.count(b'"action":"stop"'), 1)

    def test_fifth_agent_evicts_lru_unselected_nonapproval_slot(self) -> None:
        daemon = self.daemon()
        identities = [AgentIdentity("codex", str(index)) for index in range(5)]
        for identity in identities[:4]:
            self.update_agent(daemon, identity, AgentState.RUNNING)
        self.update_agent(daemon, identities[1], AgentState.WAITING_FOR_APPROVAL)

        self.update_agent(daemon, identities[4], AgentState.RUNNING)

        self.assertIsNotNone(daemon.control._sessions[identities[0]].slot)
        self.assertIsNotNone(daemon.control._sessions[identities[1]].slot)
        self.assertIsNone(daemon.control._sessions[identities[2]].slot)
        self.assertIsNotNone(daemon.control._sessions[identities[4]].slot)

    def test_terminal_state_expires_per_session(self) -> None:
        daemon = self.daemon()
        identity = AgentIdentity("codex", "session")
        self.update_agent(daemon, identity, AgentState.SUCCESS)
        daemon.control._sessions[identity].terminal_state_until = 0.0

        daemon._render_if_needed()

        self.assertIs(daemon.control.state, AgentState.WAITING_FOR_REPLY)
        self.assertIs(
            daemon.surface.views[-1].selected_state,
            AgentState.WAITING_FOR_REPLY,
        )

    def test_surface_view_exposes_only_selected_capabilities(self) -> None:
        daemon = self.daemon()
        first = AgentIdentity("codex", "first")
        second = AgentIdentity("codex", "second")
        self.update_agent(daemon, first, AgentState.RUNNING)
        self.update_agent(daemon, second, AgentState.RUNNING)
        self.add_client(daemon, first, ControlAction.STOP)
        self.add_client(daemon, second, ControlAction.RETRY)

        view = daemon._surface_view()

        self.assertEqual(view.available_actions, frozenset({ControlAction.STOP}))
        self.assertEqual(len(view.sessions), 2)
        self.assertTrue(view.sessions[0].selected)

    def test_preview_does_not_change_agent_state_or_expose_actions(self) -> None:
        daemon = self.daemon()
        identity = AgentIdentity("codex", "session")
        self.update_agent(daemon, identity, AgentState.RUNNING)
        self.add_client(daemon, identity, ControlAction.STOP)
        preview_client = Client(FakeSocket())
        daemon._clients[preview_client.socket.fileno()] = preview_client

        daemon.handle_message(
            preview_client,
            wire({
                "type": "preview",
                "preview_id": "preview-1",
                "state": "waiting_for_approval",
                "ttl": 5.0,
            }),
        )

        self.assertIs(daemon.control.state, AgentState.RUNNING)
        self.assertIs(
            daemon._surface_view().selected_state,
            AgentState.WAITING_FOR_APPROVAL,
        )
        self.assertEqual(daemon._available_actions(), frozenset())
        self.assertTrue(daemon.status_snapshot()["preview_active"])

        daemon.handle_message(
            preview_client,
            wire({"type": "preview_end", "preview_id": "preview-1"}),
        )

        self.assertIs(daemon._surface_view().selected_state, AgentState.RUNNING)
        self.assertEqual(
            daemon._available_actions(),
            frozenset({ControlAction.STOP}),
        )

    def test_preview_expires_and_disconnect_restores_authoritative_view(self) -> None:
        daemon = self.daemon()
        identity = AgentIdentity("codex", "session")
        self.update_agent(daemon, identity, AgentState.WAITING_FOR_REPLY)
        preview_client = Client(FakeSocket())
        daemon._clients[preview_client.socket.fileno()] = preview_client
        with patch("pad_lattice.daemon_runtime.time.monotonic", return_value=1.0):
            daemon.handle_message(
                preview_client,
                wire({
                    "type": "preview",
                    "preview_id": "preview-1",
                    "state": "success",
                    "ttl": 1.0,
                }),
            )

        with patch("pad_lattice.daemon_runtime.time.monotonic", return_value=2.1):
            daemon._render_if_needed()

        self.assertFalse(daemon.status_snapshot()["preview_active"])
        self.assertIs(
            daemon._surface_view().selected_state,
            AgentState.WAITING_FOR_REPLY,
        )

        daemon.handle_message(
            preview_client,
            wire({
                "type": "preview",
                "preview_id": "preview-2",
                "state": "error",
                "ttl": 5.0,
            }),
        )
        daemon._close_client(preview_client)

        self.assertFalse(daemon.status_snapshot()["preview_active"])
        self.assertIs(
            daemon._surface_view().selected_state,
            AgentState.WAITING_FOR_REPLY,
        )

    def test_actions_are_gated_by_selected_state(self) -> None:
        daemon = self.daemon()
        identity = AgentIdentity("codex", "session")
        self.update_agent(daemon, identity, AgentState.RUNNING)
        self.add_client(
            daemon,
            identity,
            ControlAction.APPROVE,
            ControlAction.STOP,
        )

        self.assertEqual(
            daemon._available_actions(),
            frozenset({ControlAction.STOP}),
        )

    def test_session_end_clears_selection_without_retargeting(self) -> None:
        daemon = self.daemon()
        first = AgentIdentity("codex", "first")
        second = AgentIdentity("codex", "second")
        self.update_agent(daemon, first, AgentState.RUNNING)
        self.update_agent(daemon, second, AgentState.WAITING_FOR_REPLY)

        subscriber = self.add_client(daemon, first, ControlAction.STOP)
        daemon.handle_message(
            Client(FakeSocket()),
            wire({
                "type": "session_end",
                "agent": {"backend": "codex", "session_id": "first"},
            }),
        )

        self.assertIsNone(daemon.control.selected_agent)
        self.assertIsNone(daemon.control.state)
        self.assertIn(second, {session.identity for session in daemon.control.sessions})
        self.assertIsNone(daemon._surface_view().selected_state)
        self.assertNotIn(subscriber.client_id, daemon.control._subscriptions)

    def test_quiet_unleased_sessions_expire_even_when_selected(self) -> None:
        daemon = self.daemon(session_ttl=10.0)
        first = AgentIdentity("codex", "first")
        second = AgentIdentity("codex", "second")
        with patch("pad_lattice.daemon_runtime.time.monotonic", return_value=1.0):
            self.update_agent(daemon, first, AgentState.RUNNING)
            self.update_agent(daemon, second, AgentState.WAITING_FOR_REPLY)

        with patch("pad_lattice.daemon_runtime.time.monotonic", return_value=12.0):
            daemon._render_if_needed()

        self.assertNotIn(first, daemon.control._sessions)
        self.assertNotIn(second, daemon.control._sessions)

    def test_live_leased_session_does_not_expire(self) -> None:
        daemon = self.daemon(session_ttl=10.0)
        identity = AgentIdentity("codex", "leased")
        lease_client = Client(FakeSocket())
        daemon._clients[lease_client.socket.fileno()] = lease_client
        with patch("pad_lattice.daemon_runtime.time.monotonic", return_value=1.0):
            daemon.handle_message(
                lease_client,
                wire({
                    "type": "session_lease",
                    "lease_id": "lease-1",
                    "agent": {"backend": "codex", "session_id": "leased"},
                }),
            )
            self.update_agent(daemon, identity, AgentState.WAITING_FOR_APPROVAL)

        with patch("pad_lattice.daemon_runtime.time.monotonic", return_value=12.0):
            daemon._render_if_needed()

        self.assertIn(identity, daemon.control._sessions)

    def test_overflow_is_reported_when_all_slots_are_protected(self) -> None:
        daemon = self.daemon()
        identities = [AgentIdentity("codex", str(index)) for index in range(5)]
        for identity in identities[:4]:
            self.update_agent(daemon, identity, AgentState.WAITING_FOR_APPROVAL)
        self.update_agent(daemon, identities[4], AgentState.RUNNING)

        view = daemon._surface_view()

        self.assertEqual(view.overflow_count, 1)
        self.assertIsNone(daemon.control._sessions[identities[4]].slot)

    def test_status_snapshot_includes_accents_and_protocol(self) -> None:
        audio = FakeAudioFeedback()
        daemon = self.daemon(activity_motion=True, audio_feedback=audio)
        identity = AgentIdentity("codex", "session")
        self.update_agent(daemon, identity, AgentState.RUNNING)

        status = daemon.status_snapshot()

        self.assertEqual(status["visual_protocol"], 1)
        self.assertTrue(status["activity_motion"])
        self.assertTrue(status["audio_feedback"])
        self.assertEqual(status["sessions"][0]["accent"], "cyan")

    def test_accents_are_unique_across_visible_sessions(self) -> None:
        daemon = self.daemon()
        for index in range(4):
            self.update_agent(daemon,
                AgentIdentity("codex", str(index)),
                AgentState.RUNNING,
            )

        accents = [session.accent for session in daemon.control.sessions]

        self.assertEqual(len(set(accents)), 4)

    def test_returning_identity_recovers_persistent_accent(self) -> None:
        with TemporaryDirectory() as directory:
            identity = AgentIdentity("codex", "returning")
            store = IdentityStore(Path(directory) / "identities.json")
            store.remember(identity, "magenta")
            daemon = PadLatticeDaemon(
                FakeSurface(),
                "/tmp/pad-lattice-unit-test.sock",
                identity_store=store,
            )
            self.daemons.append(daemon)

            self.update_agent(daemon, identity, AgentState.RUNNING)

            self.assertEqual(daemon.control._sessions[identity].accent, "magenta")

    def test_existing_non_socket_path_is_not_unlinked(self) -> None:
        with TemporaryDirectory() as directory:
            socket_path = str(Path(directory) / "daemon.sock")
            Path(socket_path).write_text("not a socket", encoding="utf-8")
            daemon = PadLatticeDaemon(FakeSurface(), socket_path)
            self.daemons.append(daemon)

            with self.assertRaisesRegex(OSError, "not a Unix socket"):
                daemon._open_server()

            self.assertTrue(Path(socket_path).exists())

    def test_server_socket_is_owner_only(self) -> None:
        with TemporaryDirectory() as directory:
            socket_path = str(Path(directory) / "daemon.sock")
            daemon = PadLatticeDaemon(FakeSurface(), socket_path)
            self.daemons.append(daemon)

            try:
                daemon._server = daemon._open_server()
            except PermissionError as exc:
                if exc.errno == errno.EPERM:
                    self.skipTest("sandbox does not permit Unix socket binding")
                raise

            mode = stat.S_IMODE(Path(socket_path).stat().st_mode)
            self.assertEqual(mode, 0o600)

    def test_partial_nonblocking_write_is_queued_until_complete(self) -> None:
        class PartialSocket(FakeSocket):
            def send(self, data: bytes) -> int:
                chunk = bytes(data[:7])
                self.sent += chunk
                return len(chunk)

        daemon = self.daemon()
        client = Client(PartialSocket())
        daemon._clients[client.socket.fileno()] = client
        message = wire_message("pong", value="x" * 40)

        daemon._send(client, message)
        self.assertTrue(client.output_buffer)
        while client.output_buffer:
            daemon._flush_client(client)

        self.assertEqual(decode_message(client.socket.sent.strip()), message)

    def test_oversized_unterminated_frame_returns_error_and_closes(self) -> None:
        class OversizedSocket(FakeSocket):
            def recv(self, size: int) -> bytes:
                return b"x" * (MAX_MESSAGE_BYTES + 1)

        daemon = self.daemon()
        client = Client(OversizedSocket())
        fileno = client.socket.fileno()
        daemon._clients[fileno] = client

        daemon._read_client(client.socket)

        response = decode_message(client.socket.sent.strip())
        self.assertEqual(response["type"], "error")
        self.assertEqual(response["code"], "frame_too_large")
        self.assertNotIn(fileno, daemon._clients)

    def test_close_is_idempotent(self) -> None:
        audio = FakeAudioFeedback()
        daemon = self.daemon(audio_feedback=audio)

        daemon.close()
        daemon.close()

        self.assertTrue(daemon.surface.closed)
        self.assertTrue(audio.closed)
