from __future__ import annotations

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
    def clear(self) -> None:
        pass


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
