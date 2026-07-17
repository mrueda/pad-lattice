from __future__ import annotations

from unittest import TestCase

from pad_lattice.events import AgentIdentity, AgentState, ControlAction
from pad_lattice.protocol import (
    ProtocolError,
    action_message,
    decode_message,
    encode_message,
    parse_action,
    parse_actions,
    parse_agent,
    parse_state,
    session_end_message,
    state_message,
    status_message,
    subscribe_actions_message,
)


class ProtocolTest(TestCase):
    def test_state_message_round_trips_as_json_line(self) -> None:
        encoded = encode_message(state_message(AgentState.WAITING_FOR_REPLY))

        self.assertEqual(
            decode_message(encoded.strip()),
            {"type": "state", "state": "waiting_for_reply"},
        )

    def test_state_message_can_include_agent_identity_and_metadata(self) -> None:
        self.assertEqual(
            state_message(
                AgentState.RUNNING,
                agent={
                    "backend": "codex",
                    "session_id": "session-123",
                    "model": "gpt-test",
                },
            ),
            {
                "type": "state",
                "state": "running",
                "agent": {
                    "backend": "codex",
                    "session_id": "session-123",
                    "model": "gpt-test",
                },
            },
        )

    def test_action_message_is_agent_scoped(self) -> None:
        identity = AgentIdentity("codex", "session-123")

        self.assertEqual(
            action_message(ControlAction.APPROVE, identity),
            {
                "type": "action",
                "action": "approve",
                "agent": {"backend": "codex", "session_id": "session-123"},
            },
        )

    def test_session_end_and_status_messages_are_explicit(self) -> None:
        identity = AgentIdentity("codex", "session-123")

        self.assertEqual(
            session_end_message(identity),
            {
                "type": "session_end",
                "agent": {"backend": "codex", "session_id": "session-123"},
            },
        )
        self.assertEqual(status_message(), {"type": "status"})

    def test_subscribe_actions_message_advertises_capabilities(self) -> None:
        identity = AgentIdentity("codex", "session-123")

        self.assertEqual(
            subscribe_actions_message(
                identity,
                (ControlAction.APPROVE, ControlAction.REJECT),
            ),
            {
                "type": "subscribe_actions",
                "agent": {"backend": "codex", "session_id": "session-123"},
                "actions": ["approve", "reject"],
            },
        )

    def test_parse_agent_rejects_incomplete_identity(self) -> None:
        with self.assertRaises(ProtocolError):
            parse_agent({"backend": "codex"}, default=None)

    def test_parse_actions_rejects_empty_capabilities(self) -> None:
        with self.assertRaises(ProtocolError):
            parse_actions([])

    def test_parse_state_rejects_unknown_state(self) -> None:
        with self.assertRaises(ProtocolError):
            parse_state("thinking")

    def test_parse_action_rejects_unknown_action(self) -> None:
        with self.assertRaises(ProtocolError):
            parse_action("merge")
