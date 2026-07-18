from __future__ import annotations

from unittest import TestCase

from pad_lattice.events import AgentIdentity, AgentState, ControlAction
from pad_lattice.protocol import (
    MAX_MESSAGE_BYTES,
    WIRE_PROTOCOL_VERSION,
    ActionEvent,
    ProtocolError,
    PreviewCommand,
    StateCommand,
    action_message,
    decode_message,
    encode_message,
    load_protocol_schema,
    parse_client_command,
    parse_action_event,
    parse_action,
    parse_actions,
    parse_agent,
    parse_state,
    preview_message,
    session_end_message,
    session_lease_message,
    state_message,
    status_message,
    subscribe_actions_message,
)


class ProtocolTest(TestCase):
    def test_machine_readable_schema_is_packaged(self) -> None:
        schema = load_protocol_schema()

        self.assertEqual(schema["title"], "Pad-Lattice Socket Protocol v1")
        self.assertEqual(schema["$defs"]["protocol"]["const"], 1)
        self.assertEqual(
            set(schema["$defs"]["state"]["enum"]),
            {state.value for state in AgentState},
        )
        self.assertEqual(
            set(schema["$defs"]["action"]["enum"]),
            {action.value for action in ControlAction},
        )

    def test_state_message_round_trips_as_json_line(self) -> None:
        encoded = encode_message(state_message(AgentState.WAITING_FOR_REPLY))

        self.assertEqual(
            decode_message(encoded.strip()),
            {
                "protocol": WIRE_PROTOCOL_VERSION,
                "type": "state",
                "state": "waiting_for_reply",
            },
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
                "protocol": WIRE_PROTOCOL_VERSION,
                "type": "state",
                "state": "running",
                "agent": {
                    "backend": "codex",
                    "session_id": "session-123",
                    "model": "gpt-test",
                },
            },
        )

    def test_state_message_can_request_a_lease_aware_ack(self) -> None:
        self.assertEqual(
            state_message(
                AgentState.RUNNING,
                agent=AgentIdentity("codex", "session-123"),
                lease_id="lease-123",
                reply=True,
            ),
            {
                "protocol": WIRE_PROTOCOL_VERSION,
                "type": "state",
                "state": "running",
                "agent": {"backend": "codex", "session_id": "session-123"},
                "lease_id": "lease-123",
                "reply": True,
            },
        )

    def test_action_message_is_agent_scoped(self) -> None:
        identity = AgentIdentity("codex", "session-123")

        self.assertEqual(
            action_message(ControlAction.APPROVE, identity),
            {
                "protocol": WIRE_PROTOCOL_VERSION,
                "type": "action",
                "action": "approve",
                "agent": {"backend": "codex", "session_id": "session-123"},
            },
        )

        self.assertEqual(
            action_message(
                ControlAction.REJECT,
                identity,
                request_id="request-1",
            )["request_id"],
            "request-1",
        )

    def test_session_end_and_status_messages_are_explicit(self) -> None:
        identity = AgentIdentity("codex", "session-123")

        self.assertEqual(
            session_end_message(identity),
            {
                "protocol": WIRE_PROTOCOL_VERSION,
                "type": "session_end",
                "agent": {"backend": "codex", "session_id": "session-123"},
            },
        )
        self.assertEqual(
            status_message(),
            {"protocol": WIRE_PROTOCOL_VERSION, "type": "status"},
        )

    def test_session_lease_can_restore_identity_and_metadata(self) -> None:
        identity = AgentIdentity("codex", "session-123")

        self.assertEqual(
            session_lease_message(
                "lease-123",
                agent=identity,
                metadata={"label": "docs"},
            ),
            {
                "protocol": WIRE_PROTOCOL_VERSION,
                "type": "session_lease",
                "lease_id": "lease-123",
                "agent": {"backend": "codex", "session_id": "session-123"},
                "metadata": {"label": "docs"},
            },
        )

    def test_subscribe_actions_message_advertises_capabilities(self) -> None:
        identity = AgentIdentity("codex", "session-123")

        self.assertEqual(
            subscribe_actions_message(
                identity,
                (ControlAction.APPROVE, ControlAction.REJECT),
            ),
            {
                "protocol": WIRE_PROTOCOL_VERSION,
                "type": "subscribe_actions",
                "agent": {"backend": "codex", "session_id": "session-123"},
                "actions": ["approve", "reject"],
            },
        )

        scoped = subscribe_actions_message(
            identity,
            (ControlAction.APPROVE, ControlAction.REJECT),
            request_id="request-1",
            one_shot=True,
        )
        self.assertEqual(scoped["request_id"], "request-1")
        self.assertTrue(scoped["one_shot"])

    def test_parse_client_command_returns_typed_state(self) -> None:
        command = parse_client_command(
            state_message(
                AgentState.RUNNING,
                agent={
                    "backend": "codex",
                    "session_id": "session-123",
                    "cwd": "/work/project",
                },
                lease_id="lease-123",
                reply=True,
            )
        )

        self.assertIsInstance(command, StateCommand)
        assert isinstance(command, StateCommand)
        self.assertEqual(command.agent, AgentIdentity("codex", "session-123"))
        self.assertEqual(command.metadata, {"cwd": "/work/project"})
        self.assertEqual(command.lease_id, "lease-123")
        self.assertTrue(command.reply)

    def test_client_command_rejects_unknown_fields(self) -> None:
        message = status_message()
        message["future"] = True

        with self.assertRaisesRegex(ProtocolError, "unknown field: future"):
            parse_client_command(message)

    def test_state_command_rejects_malformed_metadata(self) -> None:
        message = state_message(
            AgentState.RUNNING,
            agent={
                "backend": "codex",
                "session_id": "session-123",
                "label": "",
            },
        )

        with self.assertRaisesRegex(ProtocolError, "metadata values"):
            parse_client_command(message)

    def test_preview_command_is_typed_and_ttl_is_bounded(self) -> None:
        command = parse_client_command(
            preview_message(AgentState.SUCCESS, "preview-1", ttl=2.5)
        )

        self.assertEqual(
            command,
            PreviewCommand("preview-1", AgentState.SUCCESS, 2.5),
        )
        with self.assertRaises(ProtocolError):
            parse_client_command(
                preview_message(AgentState.SUCCESS, "preview-1", ttl=31)
            )

    def test_missing_or_unsupported_protocol_is_rejected(self) -> None:
        for message in (
            {"type": "status"},
            {"protocol": 2, "type": "status"},
            {"protocol": True, "type": "status"},
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(ProtocolError, "unsupported wire protocol"):
                    parse_client_command(message)

    def test_decode_rejects_unversioned_server_message(self) -> None:
        with self.assertRaises(ProtocolError) as context:
            decode_message(b'{"type":"pong"}')

        self.assertEqual(context.exception.code, "unsupported_protocol")

    def test_action_event_parser_validates_scope(self) -> None:
        identity = AgentIdentity("codex", "session-123")

        event = parse_action_event(
            action_message(
                ControlAction.APPROVE,
                identity,
                request_id="request-1",
            )
        )

        self.assertEqual(
            event,
            ActionEvent(identity, ControlAction.APPROVE, "request-1"),
        )
        with self.assertRaises(ProtocolError) as context:
            parse_action_event(status_message())
        self.assertEqual(context.exception.code, "unexpected_message_type")

    def test_encode_rejects_oversized_message(self) -> None:
        with self.assertRaises(ProtocolError) as context:
            encode_message(
                {
                    "protocol": WIRE_PROTOCOL_VERSION,
                    "type": "oversized",
                    "value": "x" * MAX_MESSAGE_BYTES,
                }
            )

        self.assertEqual(context.exception.code, "frame_too_large")

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
