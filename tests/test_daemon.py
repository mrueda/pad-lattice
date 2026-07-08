from __future__ import annotations

from unittest.mock import patch
from unittest import TestCase

from pad_lattice.daemon import Client, PadLatticeDaemon
from pad_lattice.events import AgentState, ControlAction


class FakeSocket:
    def __init__(self) -> None:
        self.sent = b""

    def sendall(self, data: bytes) -> None:
        self.sent += data

    def fileno(self) -> int:
        return 100

    def close(self) -> None:
        pass


class FakeSurface:
    def __init__(self) -> None:
        self.states = []
        self.controls_rendered = 0

    def clear(self) -> None:
        pass

    def render_state_frame(self, state, frame) -> None:
        self.states.append((state, frame))

    def render_controls(self) -> None:
        self.controls_rendered += 1


class DaemonTest(TestCase):
    def test_handle_state_message_updates_daemon_state(self) -> None:
        daemon = PadLatticeDaemon(FakeSurface(), "/tmp/pad-lattice-test.sock")
        client = Client(FakeSocket())

        daemon.handle_message(
            client,
            {"type": "state", "state": AgentState.WAITING_FOR_REPLY.value},
        )

        self.assertIs(daemon.state, AgentState.WAITING_FOR_REPLY)

    def test_handle_subscribe_message_marks_client(self) -> None:
        daemon = PadLatticeDaemon(FakeSurface(), "/tmp/pad-lattice-test.sock")
        client = Client(FakeSocket())

        daemon.handle_message(client, {"type": "subscribe_actions"})

        self.assertTrue(client.subscribed_to_actions)

    def test_handle_action_broadcasts_to_subscribers(self) -> None:
        daemon = PadLatticeDaemon(FakeSurface(), "/tmp/pad-lattice-test.sock")
        client = Client(FakeSocket(), subscribed_to_actions=True)
        daemon._clients[client.socket.fileno()] = client

        daemon._handle_action(ControlAction.APPROVE)

        self.assertIn(b'"type":"action"', client.socket.sent)
        self.assertIn(b'"action":"approve"', client.socket.sent)

    def test_handle_action_debounces_repeated_actions(self) -> None:
        daemon = PadLatticeDaemon(
            FakeSurface(),
            "/tmp/pad-lattice-test.sock",
            action_debounce=60.0,
        )
        client = Client(FakeSocket(), subscribed_to_actions=True)
        daemon._clients[client.socket.fileno()] = client

        daemon._handle_action(ControlAction.STOP)
        daemon._handle_action(ControlAction.STOP)

        self.assertEqual(client.socket.sent.count(b'"action":"stop"'), 1)

    def test_handle_action_allows_first_action_when_monotonic_is_low(self) -> None:
        daemon = PadLatticeDaemon(
            FakeSurface(),
            "/tmp/pad-lattice-test.sock",
            action_debounce=60.0,
        )
        client = Client(FakeSocket(), subscribed_to_actions=True)
        daemon._clients[client.socket.fileno()] = client

        with patch("pad_lattice.daemon.time.monotonic", return_value=1.0):
            daemon._handle_action(ControlAction.STOP)

        self.assertEqual(client.socket.sent.count(b'"action":"stop"'), 1)

    def test_terminal_state_returns_to_waiting_for_reply(self) -> None:
        surface = FakeSurface()
        daemon = PadLatticeDaemon(surface, "/tmp/pad-lattice-test.sock")

        daemon.set_state(AgentState.SUCCESS)
        daemon._terminal_state_until = 0.0
        daemon._render_if_needed()

        self.assertIs(daemon.state, AgentState.WAITING_FOR_REPLY)
        self.assertEqual(surface.states[-1][0], AgentState.WAITING_FOR_REPLY)
