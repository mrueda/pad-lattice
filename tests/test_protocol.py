from __future__ import annotations

from unittest import TestCase

from pad_lattice.events import AgentState, ControlAction
from pad_lattice.protocol import (
    ProtocolError,
    action_message,
    decode_message,
    encode_message,
    parse_action,
    parse_state,
    state_message,
    subscribe_actions_message,
)


class ProtocolTest(TestCase):
    def test_state_message_round_trips_as_json_line(self) -> None:
        encoded = encode_message(state_message(AgentState.WAITING_FOR_REPLY))

        self.assertEqual(
            decode_message(encoded.strip()),
            {"type": "state", "state": "waiting_for_reply"},
        )

    def test_action_message_uses_action_type(self) -> None:
        self.assertEqual(
            action_message(ControlAction.APPROVE),
            {"type": "action", "action": "approve"},
        )

    def test_subscribe_actions_message(self) -> None:
        self.assertEqual(subscribe_actions_message(), {"type": "subscribe_actions"})

    def test_parse_state_rejects_unknown_state(self) -> None:
        with self.assertRaises(ProtocolError):
            parse_state("thinking")

    def test_parse_action_rejects_unknown_action(self) -> None:
        with self.assertRaises(ProtocolError):
            parse_action("merge")
