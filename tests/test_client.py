from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from pad_lattice import (
    AgentIdentity,
    AgentState,
    ControlAction,
    PadLatticeClient,
)
from pad_lattice.protocol import ProtocolError, action_message, encode_message


class ClientTest(TestCase):
    def test_report_state_builds_agent_metadata(self) -> None:
        client = PadLatticeClient("/tmp/pad-lattice.sock")
        sent = []

        with patch(
            "pad_lattice.client.send_message",
            side_effect=lambda path, message: sent.append((path, message)),
        ):
            client.report_state(
                AgentState.RUNNING,
                agent=AgentIdentity("example", "session-1"),
                metadata={"label": "docs"},
            )

        self.assertEqual(sent[0][0], "/tmp/pad-lattice.sock")
        self.assertEqual(sent[0][1]["state"], "running")
        self.assertEqual(
            sent[0][1]["agent"],
            {
                "backend": "example",
                "session_id": "session-1",
                "label": "docs",
            },
        )

    def test_status_rejects_unexpected_response(self) -> None:
        client = PadLatticeClient("/tmp/pad-lattice.sock")

        with (
            patch(
                "pad_lattice.client.request_message",
                return_value={"protocol": 1, "type": "pong"},
            ),
            self.assertRaises(ProtocolError) as context,
        ):
            client.status()

        self.assertEqual(context.exception.code, "unexpected_message_type")

    def test_action_subscription_returns_typed_event(self) -> None:
        identity = AgentIdentity("codex", "session-1")

        class FakeSocket:
            def __init__(self) -> None:
                self.sent = b""
                self.response = encode_message(
                    action_message(ControlAction.STOP, identity)
                )
                self.closed = False

            def settimeout(self, timeout) -> None:
                pass

            def connect(self, path: str) -> None:
                self.path = path

            def sendall(self, data: bytes) -> None:
                self.sent += data

            def recv(self, size: int) -> bytes:
                response, self.response = self.response, b""
                return response

            def close(self) -> None:
                self.closed = True

        transport = FakeSocket()
        client = PadLatticeClient("/tmp/pad-lattice.sock")
        with patch("pad_lattice.client.socket.socket", return_value=transport):
            with client.subscribe_actions(
                identity,
                (ControlAction.STOP,),
            ) as subscription:
                event = subscription.receive()

        self.assertEqual(event.agent, identity)
        self.assertIs(event.action, ControlAction.STOP)
        self.assertIn(b'"type":"subscribe_actions"', transport.sent)
        self.assertTrue(transport.closed)
