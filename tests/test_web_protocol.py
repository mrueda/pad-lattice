from __future__ import annotations

from unittest import TestCase

from pad_lattice.devices.base import SessionIndicator, SurfaceView
from pad_lattice.events import AgentState, ControlAction
from pad_lattice.web_protocol import (
    ActionCommand,
    AuthenticateCommand,
    SelectSessionCommand,
    WebProtocolError,
    decode_web_message,
    encode_web_message,
    load_web_protocol_schema,
    parse_web_command,
    surface_message,
)


class WebProtocolTest(TestCase):
    def test_machine_readable_schema_is_packaged(self) -> None:
        schema = load_web_protocol_schema()
        self.assertEqual(schema["title"], "Pad-Lattice Web Surface Protocol v1")
        self.assertEqual(schema["$defs"]["protocol"]["const"], 1)

    def test_parses_bounded_browser_commands(self) -> None:
        auth = parse_web_command({"protocol": 1, "type": "authenticate"})
        action = parse_web_command(
            {"protocol": 1, "type": "action", "action": "approve"}
        )
        selection = parse_web_command(
            {"protocol": 1, "type": "select_session", "slot": 7}
        )
        self.assertEqual(auth, AuthenticateCommand(None))
        self.assertEqual(action, ActionCommand(ControlAction.APPROVE))
        self.assertEqual(selection, SelectSessionCommand(7))

    def test_rejects_unknown_and_oversized_messages(self) -> None:
        with self.assertRaises(WebProtocolError):
            parse_web_command({"protocol": 1, "type": "action", "action": "launch"})
        with self.assertRaises(WebProtocolError):
            parse_web_command(
                {"protocol": 1, "type": "select_session", "slot": True}
            )
        with self.assertRaisesRegex(WebProtocolError, "size limit"):
            decode_web_message("x" * (16 * 1024 + 1))

    def test_surface_message_contains_compiled_frame_and_sanitized_labels(self) -> None:
        view = SurfaceView(
            AgentState.WAITING_FOR_APPROVAL,
            sessions=(
                SessionIndicator(
                    slot=0,
                    state=AgentState.WAITING_FOR_APPROVAL,
                    selected=True,
                    accent="cyan",
                    label="  Reviewer\nagent  ",
                ),
            ),
            available_actions=frozenset(
                {ControlAction.APPROVE, ControlAction.REJECT}
            ),
        )
        message = surface_message(view, 8)
        self.assertEqual(
            message["view"]["sessions"][0]["label"],
            "Reviewer agent",
        )
        self.assertNotIn("session_id", message["view"]["sessions"][0])
        self.assertEqual(
            message["visual_frame"]["actions"]["approve"],
            "action:approve:enabled",
        )

    def test_outbound_messages_are_bounded(self) -> None:
        with self.assertRaisesRegex(WebProtocolError, "size limit"):
            encode_web_message({"protocol": 1, "type": "error", "error": "x" * 20_000})
