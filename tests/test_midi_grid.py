from __future__ import annotations

from dataclasses import dataclass
from unittest import TestCase
from unittest.mock import patch

from pad_lattice.devices.base import (
    ActionPressed,
    SessionIndicator,
    SessionSelected,
    ShowColor,
    ShowFrame,
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


def show_color(
    fallback: str,
    rgb: tuple[int, int, int],
) -> ShowColor:
    return ShowColor(fallback, rgb)


class MidiGridSurfaceTest(TestCase):
    def test_mk1_initialization_enters_standalone_programmer_mode(self) -> None:
        surface, output, _ = surface_for("novation/launchpad/pro-mk1")

        surface.initialize()

        self.assertEqual(output.messages[0].type, "sysex")
        self.assertEqual(output.messages[0].data, [0, 32, 41, 2, 16, 33, 1])
        self.assertEqual(output.messages[1].data, [0, 32, 41, 2, 16, 44, 3])

    def test_mk1_close_restores_live_session_mode(self) -> None:
        surface, output, _ = surface_for("novation/launchpad/pro-mk1")

        surface.close()

        self.assertEqual(output.messages[-2].data, [0, 32, 41, 2, 16, 34, 0])
        self.assertEqual(output.messages[-1].data, [0, 32, 41, 2, 16, 33, 0])

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

    def test_identical_frames_do_not_resend_midi_values(self) -> None:
        surface, output, _ = surface_for("novation/launchpad/pro-mk1")
        view = SurfaceView(AgentState.WAITING_FOR_REPLY)

        surface.render(view)
        first_frame_messages = len(output.messages)
        surface.render(view)

        self.assertGreater(first_frame_messages, 0)
        self.assertEqual(len(output.messages), first_frame_messages)

    def test_changed_frame_sends_only_address_differences(self) -> None:
        surface, output, _ = surface_for("novation/launchpad/pro-mk1")

        surface.render(SurfaceView(AgentState.WAITING_FOR_REPLY))
        full_frame_messages = len(output.messages)
        output.messages.clear()
        surface.render(SurfaceView(AgentState.SUCCESS))

        self.assertGreater(len(output.messages), 0)
        self.assertLess(len(output.messages), full_frame_messages)

    def test_show_frame_uses_the_full_grid_and_both_outer_rails(self) -> None:
        surface, output, _ = surface_for("novation/launchpad/mini-mk3")
        cyan = show_color("accent:cyan:selected", (0, 220, 255))
        orange = show_color("accent:orange:selected", (255, 92, 18))
        magenta = show_color("accent:magenta:selected", (255, 35, 178))
        frame = ShowFrame(
            grid=tuple(tuple(cyan for _ in range(8)) for _ in range(8)),
            top=(orange,) * 8,
            right=(magenta,) * 8,
        )

        surface.render_show_frame(frame)
        first_message_count = len(output.messages)
        surface.render_show_frame(frame)

        latest_notes = {
            message.note: message.velocity
            for message in output.messages
            if message.type == "note_on"
        }
        latest_ccs = {
            message.control: message.value
            for message in output.messages
            if message.type == "control_change"
        }
        self.assertEqual(len(latest_notes), 64)
        self.assertEqual(set(latest_ccs), {91, 92, 93, 94, 95, 96, 97, 98, 89, 79, 69, 59, 49, 39, 29, 19})
        self.assertEqual(
            set(latest_notes.values()),
            {surface.profile.accent("cyan").selected},
        )
        self.assertEqual(latest_ccs[93], surface.profile.accent("orange").selected)
        self.assertEqual(latest_ccs[79], surface.profile.accent("magenta").selected)
        self.assertEqual(len(output.messages), first_message_count)

    def test_mk1_show_batches_and_caches_direct_rgb_sysex(self) -> None:
        surface, output, _ = surface_for("novation/launchpad/pro-mk1")
        amber = show_color("accent:orange:selected", (255, 128, 0))
        frame = ShowFrame(
            grid=tuple(tuple(amber for _ in range(8)) for _ in range(8)),
            top=(amber,) * 8,
            right=(amber,) * 8,
        )

        surface.render_show_frame(frame)
        first_message_count = len(output.messages)
        surface.render_show_frame(frame)

        self.assertEqual(first_message_count, 2)
        self.assertEqual(len(output.messages), first_message_count)
        self.assertEqual(output.messages[0].type, "sysex")
        self.assertEqual(output.messages[0].data[:6], [0, 32, 41, 2, 16, 11])
        self.assertEqual(output.messages[0].data[6:10], [81, 63, 32, 0])
        self.assertEqual(len(output.messages[0].data), 6 + 78 * 4)
        self.assertEqual(len(output.messages[1].data), 6 + 2 * 4)

    def test_semantic_render_clears_show_only_rail_lights(self) -> None:
        surface, output, _ = surface_for("novation/launchpad/pro-mk1")
        off = show_color("off", (0, 0, 0))
        lit = show_color("accent:rose:selected", (255, 66, 102))
        surface.render_show_frame(
            ShowFrame(
                grid=tuple(tuple(off for _ in range(8)) for _ in range(8)),
                top=(lit,) * 8,
                right=(lit,) * 8,
            )
        )

        surface.render(SurfaceView(AgentState.WAITING_FOR_REPLY))

        latest_ccs = {
            message.control: message.value
            for message in output.messages
            if message.type == "control_change"
        }
        self.assertEqual(latest_ccs[93], surface.profile.color("off"))
        self.assertEqual(latest_ccs[94], surface.profile.color("off"))
        self.assertEqual(latest_ccs[96], surface.profile.color("off"))

    def test_render_draws_session_accents_and_semantic_statuses(self) -> None:
        surface, output, _ = surface_for("novation/launchpad/pro-mk1")
        view = SurfaceView(
            AgentState.RUNNING,
            sessions=(
                SessionIndicator(0, AgentState.RUNNING, selected=True, accent="cyan"),
                SessionIndicator(
                    1,
                    AgentState.WAITING_FOR_APPROVAL,
                    accent="magenta",
                ),
            ),
        )

        surface.render(view)

        latest_notes = {
            message.note: message.velocity
            for message in output.messages
            if message.type == "note_on"
        }
        latest_ccs = {
            message.control: message.value
            for message in output.messages
            if message.type == "control_change"
        }
        self.assertEqual(latest_ccs[89], surface.profile.accent("cyan").selected)
        self.assertEqual(latest_ccs[79], surface.profile.accent("magenta").unselected)
        self.assertEqual(
            latest_notes[88],
            surface.profile.color("state:running:summary"),
        )
        self.assertEqual(
            latest_notes[78],
            surface.profile.color("state:waiting_for_approval:summary"),
        )

    def test_actions_are_bright_only_when_available(self) -> None:
        surface, output, _ = surface_for("novation/launchpad/pro-mk1")

        surface.render(
            SurfaceView(
                AgentState.WAITING_FOR_APPROVAL,
                available_actions=frozenset({ControlAction.APPROVE}),
            )
        )

        latest = {
            message.control: message.value
            for message in output.messages
            if message.type == "control_change"
        }
        self.assertEqual(
            latest[91], surface.profile.color("action:approve:enabled")
        )
        self.assertEqual(
            latest[92], surface.profile.color("off")
        )

    def test_poll_events_distinguishes_actions_and_session_selection(self) -> None:
        surface, _, input_port = surface_for("novation/launchpad/pro-mk1")
        input_port.pending.extend(
            [
                FakeMessage("control_change", control=91, value=127),
                FakeMessage("control_change", control=79, value=127),
                FakeMessage("control_change", control=69, value=0),
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
            and message.velocity == surface.profile.color("state:success:primary")
        }
        self.assertEqual(
            green_notes,
            {
                surface.profile.grid_address(x, y).number
                for x, y in (
                    (1, 2),
                    (5, 2),
                    (0, 4),
                    (1, 5),
                    (2, 6),
                    (3, 7),
                    (4, 6),
                    (5, 5),
                    (6, 4),
                )
            },
        )

    def test_overflow_indicator_is_steady_amber(self) -> None:
        surface, output, _ = surface_for("novation/launchpad/pro-mk1")

        surface.render(SurfaceView(None, overflow_count=1))

        latest_ccs = {
            message.control: message.value
            for message in output.messages
            if message.type == "control_change"
        }
        self.assertEqual(latest_ccs[95], surface.profile.color("system:overflow"))

    def test_running_motion_is_opt_in(self) -> None:
        surface, output, _ = surface_for("novation/launchpad/pro-mk1")

        surface.render(
            SurfaceView(AgentState.RUNNING, frame=1, activity_motion=True)
        )

        activity_notes = {
            message.note
            for message in output.messages
            if message.type == "note_on"
            and message.velocity == surface.profile.color("activity")
        }
        self.assertEqual(
            activity_notes,
            {
                surface.profile.grid_address(x, y).number
                for x in (3,)
                for y in (3, 4)
            },
        )

    def test_text_columns_build_a_scrollable_glyph(self) -> None:
        columns = _text_columns("I")

        self.assertEqual(len(columns), 6)
        self.assertNotEqual(columns[0], 0)
        self.assertEqual(columns[-1], 0)

    def test_greeting_duration_matches_every_rendered_scroll_frame(self) -> None:
        surface, _, _ = surface_for("novation/launchpad/pro-mk1")
        surface.startup_greeting = "HELLO FROM CODEX CLI"
        surface.scroll_delay = 0.08

        self.assertAlmostEqual(surface.startup_greeting_duration, 10.32)

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
