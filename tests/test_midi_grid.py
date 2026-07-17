from __future__ import annotations

from dataclasses import dataclass
from unittest import TestCase
from unittest.mock import patch

from pad_lattice.devices.base import (
    ActionPressed,
    SessionIndicator,
    SessionSelected,
    SurfaceView,
)
from pad_lattice.devices.midi_grid import (
    MidiDeviceError,
    MidiGridSurface,
    _text_columns,
    open_midi_grid_surface,
)
from pad_lattice.devices.profiles import ProfileCatalog
from pad_lattice.events import AgentState, ControlAction


@dataclass
class FakeMessage:
    type: str
    channel: int = 0
    note: int = -1
    velocity: int = 0
    control: int = -1
    value: int = 0
    data: list[int] | None = None


def fake_message(message_type: str, **kwargs) -> FakeMessage:
    return FakeMessage(message_type, **kwargs)


class FakePort:
    def __init__(self) -> None:
        self.messages: list[FakeMessage] = []
        self.pending: list[FakeMessage] = []
        self.closed = False

    def send(self, message: FakeMessage) -> None:
        self.messages.append(message)

    def iter_pending(self):
        pending, self.pending = self.pending, []
        return pending

    def close(self) -> None:
        self.closed = True


def surface_for(profile_id: str) -> tuple[MidiGridSurface, FakePort, FakePort]:
    profile = ProfileCatalog.load(include_user=False).get(profile_id)
    output = FakePort()
    input_port = FakePort()
    surface = MidiGridSurface(
        profile,
        output,
        input_port,
        input_name="input",
        output_name="output",
        message_factory=fake_message,
        startup_greeting=None,
    )
    return surface, output, input_port


class MidiGridSurfaceTest(TestCase):
    def test_mk1_initialization_preserves_host_mode_messages(self) -> None:
        surface, output, _ = surface_for("novation/launchpad/pro-mk1")

        surface.initialize()

        self.assertEqual(output.messages[0].type, "sysex")
        self.assertEqual(output.messages[0].data, [0, 32, 41, 2, 16, 33, 0])
        self.assertEqual(output.messages[1].data, [0, 32, 41, 2, 16, 34, 0])
        self.assertEqual(output.messages[2].type, "control_change")
        self.assertEqual(output.messages[2].control, 0)
        self.assertEqual(output.messages[2].value, 0)

    def test_mini_close_clears_restores_live_mode_and_closes_ports(self) -> None:
        surface, output, input_port = surface_for("novation/launchpad/mini-mk3")

        surface.close()

        self.assertEqual(output.messages[-1].type, "sysex")
        self.assertEqual(output.messages[-1].data, [0, 32, 41, 2, 13, 14, 0])
        self.assertTrue(output.closed)
        self.assertTrue(input_port.closed)

    def test_render_uses_only_static_midi_channel(self) -> None:
        surface, output, _ = surface_for("novation/launchpad/pro-mk1")

        surface.render(SurfaceView(AgentState.RUNNING, frame=2))

        lit = [
            message
            for message in output.messages
            if message.type == "note_on" and message.velocity
        ]
        self.assertTrue(lit)
        self.assertEqual({message.channel for message in lit}, {0})

    def test_render_draws_session_accents_and_semantic_statuses(self) -> None:
        surface, output, _ = surface_for("novation/launchpad/pro-mk1")
        view = SurfaceView(
            AgentState.RUNNING,
            sessions=(
                SessionIndicator(0, AgentState.RUNNING, selected=True),
                SessionIndicator(1, AgentState.WAITING_FOR_APPROVAL),
            ),
        )

        surface.render(view)

        latest = {
            message.note: message.velocity
            for message in output.messages
            if message.type == "note_on"
        }
        self.assertEqual(latest[13], surface.profile.accents[0].bright)
        self.assertEqual(latest[14], surface.profile.accents[1].dim)
        self.assertEqual(latest[23], surface.profile.color("blue"))
        self.assertEqual(latest[24], surface.profile.color("yellow"))

    def test_actions_are_bright_only_when_available(self) -> None:
        surface, output, _ = surface_for("novation/launchpad/pro-mk1")

        surface.render(
            SurfaceView(
                AgentState.WAITING_FOR_APPROVAL,
                available_actions=frozenset({ControlAction.APPROVE}),
            )
        )

        latest = {
            message.note: message.velocity
            for message in output.messages
            if message.type == "note_on"
        }
        self.assertEqual(latest[11], surface.profile.color("green"))
        self.assertEqual(latest[12], surface.profile.color("dim_red"))

    def test_poll_events_distinguishes_actions_and_session_selection(self) -> None:
        surface, _, input_port = surface_for("novation/launchpad/pro-mk1")
        input_port.pending.extend(
            [
                FakeMessage("note_on", note=11, velocity=127),
                FakeMessage("note_on", note=14, velocity=127),
                FakeMessage("note_on", note=15, velocity=0),
            ]
        )

        self.assertEqual(
            surface.poll_events(),
            [ActionPressed(ControlAction.APPROVE), SessionSelected(1)],
        )

    def test_success_state_uses_a_green_happy_face(self) -> None:
        surface, output, _ = surface_for("novation/launchpad/pro-mk1")

        surface.render(SurfaceView(AgentState.SUCCESS))

        green_notes = {
            message.note
            for message in output.messages
            if message.type == "note_on"
            and message.velocity == surface.profile.color("green")
        }
        self.assertEqual(
            green_notes,
            {
                surface.profile.grid_address(x, y).number
                for x, y in (
                    (2, 1),
                    (5, 1),
                    (1, 3),
                    (2, 4),
                    (3, 5),
                    (4, 5),
                    (5, 4),
                    (6, 3),
                )
            },
        )

    def test_text_columns_build_a_scrollable_glyph(self) -> None:
        columns = _text_columns("I")

        self.assertEqual(len(columns), 6)
        self.assertNotEqual(columns[0], 0)
        self.assertEqual(columns[-1], 0)

    def test_failed_input_open_closes_the_already_open_output(self) -> None:
        profile = ProfileCatalog.load(include_user=False).get(
            "novation/launchpad/pro-mk1"
        )
        output = FakePort()

        class FailingBackend:
            @staticmethod
            def open_output(name):
                return output

            @staticmethod
            def open_input(name):
                raise OSError("input unavailable")

        with (
            patch(
                "pad_lattice.devices.midi_grid._import_mido",
                return_value=FailingBackend(),
            ),
            self.assertRaisesRegex(MidiDeviceError, "could not open MIDI input"),
        ):
            open_midi_grid_surface(
                profile,
                input_name="input",
                output_name="output",
            )

        self.assertTrue(output.closed)
