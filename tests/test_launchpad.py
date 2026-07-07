from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from pad_lattice.events import AgentState, ControlAction
from pad_lattice.launchpad import (
    LaunchpadPalette,
    LaunchpadSurface,
    PadLayout,
    _grid_note,
    _pick_port,
    _text_columns,
)


class FakeOutput:
    def __init__(self) -> None:
        self.messages = []

    def send(self, message) -> None:
        self.messages.append(message)


class FakeMessage:
    def __init__(self, message_type: str, **kwargs: int) -> None:
        self.type = message_type
        for key, value in kwargs.items():
            setattr(self, key, value)


def fake_message(message_type: str, **kwargs: int) -> FakeMessage:
    return FakeMessage(message_type, **kwargs)


class LaunchpadSurfaceTest(TestCase):
    def test_action_from_message_maps_mvp_controls(self) -> None:
        surface = LaunchpadSurface(FakeOutput(), layout=PadLayout(), message_factory=fake_message)

        self.assertEqual(
            surface.action_from_message(FakeMessage("note_on", note=11, velocity=127)),
            ControlAction.APPROVE,
        )
        self.assertEqual(
            surface.action_from_message(FakeMessage("note_on", note=12, velocity=127)),
            ControlAction.REJECT,
        )
        self.assertEqual(
            surface.action_from_message(FakeMessage("note_on", note=18, velocity=127)),
            ControlAction.STOP,
        )
        self.assertEqual(
            surface.action_from_message(FakeMessage("note_on", note=17, velocity=127)),
            ControlAction.RETRY,
        )

    def test_action_from_message_ignores_releases_and_other_messages(self) -> None:
        surface = LaunchpadSurface(FakeOutput(), layout=PadLayout(), message_factory=fake_message)

        self.assertIsNone(
            surface.action_from_message(FakeMessage("note_on", note=11, velocity=0))
        )
        self.assertIsNone(
            surface.action_from_message(FakeMessage("control_change", control=11, value=127))
        )
        self.assertIsNone(
            surface.action_from_message(FakeMessage("note_on", note=99, velocity=127))
        )

    def test_render_success_state_uses_happy_face_shape(self) -> None:
        output = FakeOutput()
        surface = LaunchpadSurface(output, layout=PadLayout(), message_factory=fake_message)

        surface.render_state(AgentState.SUCCESS)

        green_notes = {message.note for message in output.messages if message.velocity}
        self.assertEqual(
            green_notes,
            {
                _grid_note(2, 1),
                _grid_note(5, 1),
                _grid_note(1, 4),
                _grid_note(2, 5),
                _grid_note(3, 5),
                _grid_note(4, 5),
                _grid_note(5, 5),
                _grid_note(6, 4),
            },
        )

    def test_render_error_state_uses_x_shape(self) -> None:
        output = FakeOutput()
        surface = LaunchpadSurface(output, layout=PadLayout(), message_factory=fake_message)

        surface.render_state(AgentState.ERROR)

        red_notes = {message.note for message in output.messages if message.velocity}
        self.assertIn(_grid_note(0, 0), red_notes)
        self.assertIn(_grid_note(7, 0), red_notes)
        self.assertIn(_grid_note(3, 3), red_notes)
        self.assertIn(_grid_note(4, 3), red_notes)

    def test_render_waiting_state_uses_steady_frame(self) -> None:
        output = FakeOutput()
        surface = LaunchpadSurface(output, layout=PadLayout(), message_factory=fake_message)

        surface.render_state_frame(AgentState.WAITING_FOR_APPROVAL, 0)

        lit_velocities = {message.velocity for message in output.messages if message.velocity}
        self.assertEqual(lit_velocities, {LaunchpadPalette.YELLOW})
        lit_notes = {message.note for message in output.messages if message.velocity}
        self.assertEqual(
            lit_notes,
            {
                _grid_note(3, 1),
                _grid_note(4, 1),
                _grid_note(5, 2),
                _grid_note(4, 3),
                _grid_note(4, 5),
                _grid_note(3, 5),
            },
        )

    def test_render_waiting_for_reply_uses_white_question_mark(self) -> None:
        output = FakeOutput()
        surface = LaunchpadSurface(output, layout=PadLayout(), message_factory=fake_message)

        surface.render_state_frame(AgentState.WAITING_FOR_REPLY, 0)

        white_notes = {
            message.note
            for message in output.messages
            if message.velocity == LaunchpadPalette.WHITE
        }
        self.assertIn(_grid_note(2, 0), white_notes)
        self.assertIn(_grid_note(3, 0), white_notes)
        self.assertIn(_grid_note(5, 0), white_notes)
        self.assertIn(_grid_note(5, 2), white_notes)
        self.assertIn(_grid_note(3, 6), white_notes)
        self.assertIn(_grid_note(4, 6), white_notes)

    def test_render_running_state_uses_steady_symbol_with_activity_dot(self) -> None:
        output = FakeOutput()
        surface = LaunchpadSurface(output, layout=PadLayout(), message_factory=fake_message)

        surface.render_state_frame(AgentState.RUNNING, 2)

        blue_notes = {
            message.note
            for message in output.messages
            if message.velocity == LaunchpadPalette.BLUE
        }
        self.assertEqual(
            blue_notes,
            {
                _grid_note(3, 2),
                _grid_note(4, 2),
                _grid_note(3, 3),
                _grid_note(4, 3),
            },
        )
        white_notes = {
            message.note
            for message in output.messages
            if message.velocity == LaunchpadPalette.WHITE
        }
        self.assertEqual(white_notes, {_grid_note(2, 0)})

    def test_render_user_typing_uses_input_line(self) -> None:
        output = FakeOutput()
        surface = LaunchpadSurface(output, layout=PadLayout(), message_factory=fake_message)

        surface.render_state_frame(AgentState.USER_TYPING, 0)

        white_notes = {
            message.note
            for message in output.messages
            if message.velocity == LaunchpadPalette.WHITE
        }
        self.assertEqual(
            white_notes,
            {_grid_note(x, 5) for x in range(1, 7)} | {_grid_note(6, 4)},
        )


class MessagePatchTest(TestCase):
    def test_render_controls_sends_expected_notes(self) -> None:
        output = FakeOutput()
        surface = LaunchpadSurface(output, layout=PadLayout(), message_factory=fake_message)

        surface._send_note_on = lambda note, velocity: output.send(
            SimpleNamespace(type="note_on", note=note, velocity=velocity)
        )
        surface.render_controls()

        self.assertEqual([message.note for message in output.messages], [11, 12, 18, 17])


class PortSelectionTest(TestCase):
    def test_pick_port_prefers_launchpad_pro_live_port(self) -> None:
        self.assertEqual(
            _pick_port(
                [
                    "Launchpad Pro:Launchpad Pro Standalone Port 20:1",
                    "Launchpad Pro:Launchpad Pro Live Port 20:0",
                    "Launchpad Pro:Launchpad Pro MIDI Port 20:2",
                ],
                "output",
            ),
            "Launchpad Pro:Launchpad Pro Live Port 20:0",
        )

    def test_initialize_enters_host_mode_before_rendering_controls(self) -> None:
        output = FakeOutput()
        surface = LaunchpadSurface(
            output,
            layout=PadLayout(),
            message_factory=fake_message,
            startup_greeting=None,
        )

        surface.initialize()

        self.assertEqual(output.messages[0].type, "sysex")
        self.assertEqual(output.messages[0].data, [0, 32, 41, 2, 16, 33, 0])
        self.assertEqual(output.messages[1].type, "sysex")
        self.assertEqual(output.messages[1].data, [0, 32, 41, 2, 16, 34, 0])

    def test_text_columns_build_a_scrollable_glyph(self) -> None:
        columns = _text_columns("I")

        self.assertEqual(len(columns), 6)
        self.assertNotEqual(columns[0], 0)
        self.assertEqual(columns[-1], 0)

    def test_render_text_frame_maps_pixels_to_grid_notes(self) -> None:
        output = FakeOutput()
        surface = LaunchpadSurface(
            output,
            layout=PadLayout(),
            message_factory=fake_message,
            startup_greeting=None,
        )

        surface.render_text_frame([0b01000000, 0, 0, 0, 0, 0, 0, 0], LaunchpadPalette.GREEN)

        lit_messages = [message for message in output.messages if message.velocity]
        self.assertEqual(len(lit_messages), 1)
        self.assertEqual(lit_messages[0].note, _grid_note(0, 1))
        self.assertEqual(lit_messages[0].velocity, LaunchpadPalette.GREEN)
