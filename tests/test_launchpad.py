from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from pad_lattice.events import AgentState, ControlAction
from pad_lattice.launchpad import LaunchpadPalette, LaunchpadSurface, PadLayout


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

    def test_render_state_uses_expected_state_color(self) -> None:
        output = FakeOutput()
        surface = LaunchpadSurface(output, layout=PadLayout(), message_factory=fake_message)

        surface.render_state(AgentState.WAITING_FOR_APPROVAL)

        self.assertEqual(len(output.messages), 4)
        self.assertTrue(
            all(message.velocity == LaunchpadPalette.YELLOW for message in output.messages)
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
