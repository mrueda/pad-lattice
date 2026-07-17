from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from pad_lattice.daemon import Client, PadLatticeDaemon
from pad_lattice.devices.base import SessionSelected
from pad_lattice.events import AgentIdentity, AgentState, ControlAction


class FakeSocket:
    _next_fileno = 100

    def __init__(self) -> None:
        self.sent = b""
        self._fileno = self._next_fileno
        FakeSocket._next_fileno += 1

    def sendall(self, data: bytes) -> None:
        self.sent += data

    def fileno(self) -> int:
        return self._fileno

    def close(self) -> None:
        pass


class FakeSurface:
    profile_id = "test/grid/device"
    input_name = "Test input"
    output_name = "Test output"
    selector_capacity = 4

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
        client = Client(FakeSocket(), agent=identity, actions=frozenset(actions))
        daemon._clients[client.socket.fileno()] = client
        return client

    def test_state_message_registers_agent_identity(self) -> None:
        daemon = self.daemon()
        client = Client(FakeSocket())

        daemon.handle_message(
            client,
            {
                "type": "state",
                "state": "running",
                "agent": {"backend": "codex", "session_id": "session-1"},
            },
        )

        self.assertEqual(daemon.selected_agent, AgentIdentity("codex", "session-1"))
        self.assertIs(daemon.state, AgentState.RUNNING)

    def test_subscribe_message_records_target_and_capabilities(self) -> None:
        daemon = self.daemon()
        client = Client(FakeSocket())

        daemon.handle_message(
            client,
            {
                "type": "subscribe_actions",
                "agent": {"backend": "codex", "session_id": "session-1"},
                "actions": ["approve", "reject"],
            },
        )

        self.assertEqual(client.agent, AgentIdentity("codex", "session-1"))
        self.assertEqual(
            client.actions,
            frozenset({ControlAction.APPROVE, ControlAction.REJECT}),
        )

    def test_background_update_does_not_steal_selection(self) -> None:
        daemon = self.daemon()
        first = AgentIdentity("codex", "first")
        second = AgentIdentity("codex", "second")

        daemon.update_agent(first, AgentState.WAITING_FOR_REPLY)
        daemon.update_agent(second, AgentState.RUNNING)

        self.assertEqual(daemon.selected_agent, first)
        self.assertIs(daemon.state, AgentState.WAITING_FOR_REPLY)

    def test_selector_changes_the_active_session(self) -> None:
        daemon = self.daemon()
        first = AgentIdentity("codex", "first")
        second = AgentIdentity("codex", "second")
        daemon.update_agent(first, AgentState.WAITING_FOR_REPLY)
        daemon.update_agent(second, AgentState.RUNNING)
        second_slot = daemon._sessions[second].slot
        assert second_slot is not None

        daemon._handle_surface_event(SessionSelected(second_slot))

        self.assertEqual(daemon.selected_agent, second)
        self.assertIs(daemon.state, AgentState.RUNNING)

    def test_action_is_sent_only_to_selected_matching_subscriber(self) -> None:
        daemon = self.daemon()
        first = AgentIdentity("codex", "first")
        second = AgentIdentity("codex", "second")
        daemon.update_agent(first, AgentState.WAITING_FOR_APPROVAL)
        daemon.update_agent(second, AgentState.WAITING_FOR_APPROVAL)
        first_client = self.add_client(daemon, first, ControlAction.APPROVE)
        second_client = self.add_client(daemon, second, ControlAction.APPROVE)

        daemon._handle_action(ControlAction.APPROVE)

        self.assertIn(b'"action":"approve"', first_client.socket.sent)
        self.assertIn(b'"session_id":"first"', first_client.socket.sent)
        self.assertEqual(second_client.socket.sent, b"")

    def test_unavailable_action_is_not_emitted(self) -> None:
        daemon = self.daemon()
        identity = AgentIdentity("codex", "session")
        daemon.update_agent(identity, AgentState.WAITING_FOR_APPROVAL)
        client = self.add_client(daemon, identity, ControlAction.REJECT)

        daemon._handle_action(ControlAction.APPROVE)

        self.assertEqual(client.socket.sent, b"")

    def test_handle_action_debounces_repeated_actions(self) -> None:
        daemon = self.daemon(action_debounce=60.0)
        identity = AgentIdentity("codex", "session")
        daemon.update_agent(identity, AgentState.RUNNING)
        client = self.add_client(daemon, identity, ControlAction.STOP)

        daemon._handle_action(ControlAction.STOP)
        daemon._handle_action(ControlAction.STOP)

        self.assertEqual(client.socket.sent.count(b'"action":"stop"'), 1)

    def test_first_action_is_allowed_when_monotonic_is_low(self) -> None:
        daemon = self.daemon(action_debounce=60.0)
        identity = AgentIdentity("codex", "session")
        daemon.update_agent(identity, AgentState.RUNNING)
        client = self.add_client(daemon, identity, ControlAction.STOP)

        with patch("pad_lattice.daemon.time.monotonic", return_value=1.0):
            daemon._handle_action(ControlAction.STOP)

        self.assertEqual(client.socket.sent.count(b'"action":"stop"'), 1)

    def test_debounce_is_scoped_to_agent_identity(self) -> None:
        daemon = self.daemon(action_debounce=60.0)
        first = AgentIdentity("codex", "first")
        second = AgentIdentity("codex", "second")
        daemon.update_agent(first, AgentState.RUNNING)
        daemon.update_agent(second, AgentState.RUNNING)
        first_client = self.add_client(daemon, first, ControlAction.STOP)
        second_client = self.add_client(daemon, second, ControlAction.STOP)

        daemon._handle_action(ControlAction.STOP)
        second_slot = daemon._sessions[second].slot
        assert second_slot is not None
        daemon.select_slot(second_slot)
        daemon._handle_action(ControlAction.STOP)

        self.assertEqual(first_client.socket.sent.count(b'"action":"stop"'), 1)
        self.assertEqual(second_client.socket.sent.count(b'"action":"stop"'), 1)

    def test_fifth_agent_evicts_lru_unselected_nonapproval_slot(self) -> None:
        daemon = self.daemon()
        identities = [AgentIdentity("codex", str(index)) for index in range(5)]
        for identity in identities[:4]:
            daemon.update_agent(identity, AgentState.RUNNING)
        daemon.update_agent(identities[1], AgentState.WAITING_FOR_APPROVAL)

        daemon.update_agent(identities[4], AgentState.RUNNING)

        self.assertIsNotNone(daemon._sessions[identities[0]].slot)
        self.assertIsNotNone(daemon._sessions[identities[1]].slot)
        self.assertIsNone(daemon._sessions[identities[2]].slot)
        self.assertIsNotNone(daemon._sessions[identities[4]].slot)

    def test_terminal_state_expires_per_session(self) -> None:
        daemon = self.daemon()
        identity = AgentIdentity("codex", "session")
        daemon.update_agent(identity, AgentState.SUCCESS)
        daemon._sessions[identity].terminal_state_until = 0.0

        daemon._render_if_needed()

        self.assertIs(daemon.state, AgentState.WAITING_FOR_REPLY)
        self.assertIs(
            daemon.surface.views[-1].selected_state,
            AgentState.WAITING_FOR_REPLY,
        )

    def test_surface_view_exposes_only_selected_capabilities(self) -> None:
        daemon = self.daemon()
        first = AgentIdentity("codex", "first")
        second = AgentIdentity("codex", "second")
        daemon.update_agent(first, AgentState.RUNNING)
        daemon.update_agent(second, AgentState.RUNNING)
        self.add_client(daemon, first, ControlAction.STOP)
        self.add_client(daemon, second, ControlAction.RETRY)

        view = daemon._surface_view()

        self.assertEqual(view.available_actions, frozenset({ControlAction.STOP}))
        self.assertEqual(len(view.sessions), 2)
        self.assertTrue(view.sessions[0].selected)

    def test_close_is_idempotent(self) -> None:
        daemon = self.daemon()

        daemon.close()
        daemon.close()

        self.assertTrue(daemon.surface.closed)
