"""Launchpad Pro MIDI renderer and input controller."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pad_lattice.events import AgentState, ControlAction

MidiMessage = Any


class LaunchpadError(RuntimeError):
    """Raised when Launchpad MIDI setup fails."""


@dataclass(frozen=True)
class PadLayout:
    """MVP pad assignments.

    Note numbers follow Launchpad Pro programmer-style grid numbering where the
    bottom-left grid pad is 11 and the top-right grid pad is 88.
    """

    status_pads: tuple[int, ...] = (44, 45, 54, 55)
    approve: int = 11
    reject: int = 12
    stop: int = 18
    retry: int = 17

    @property
    def controls(self) -> dict[int, ControlAction]:
        return {
            self.approve: ControlAction.APPROVE,
            self.reject: ControlAction.REJECT,
            self.stop: ControlAction.STOP,
            self.retry: ControlAction.RETRY,
        }


class LaunchpadPalette:
    """Launchpad color indices for the small MVP state/control surface."""

    OFF = 0
    BLUE = 45
    YELLOW = 13
    GREEN = 21
    RED = 5
    WHITE = 3
    DIM_GREEN = 17
    DIM_RED = 7
    DIM_YELLOW = 9
    DIM_BLUE = 41

    STATE_COLORS: dict[AgentState, int] = {
        AgentState.RUNNING: BLUE,
        AgentState.WAITING_FOR_APPROVAL: YELLOW,
        AgentState.SUCCESS: GREEN,
        AgentState.ERROR: RED,
    }


FONT_5X7: dict[str, tuple[str, ...]] = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
}


class LaunchpadSurface:
    """Render agent state and translate Launchpad presses into actions."""

    def __init__(
        self,
        output_port: Any,
        input_port: Any | None = None,
        *,
        layout: PadLayout | None = None,
        palette: type[LaunchpadPalette] = LaunchpadPalette,
        message_factory: Callable[..., MidiMessage] | None = None,
        startup_greeting: str | None = "HELLO FROM CODEX CLI",
        scroll_delay: float = 0.08,
    ) -> None:
        self.output_port = output_port
        self.input_port = input_port
        self.layout = layout or PadLayout()
        self.palette = palette
        self._message_factory = message_factory or _message
        self.startup_greeting = startup_greeting
        self.scroll_delay = scroll_delay

    def initialize(self) -> None:
        self.enter_host_mode()
        self.clear()
        if self.startup_greeting:
            self.scroll_text(self.startup_greeting, self.palette.GREEN, self.scroll_delay)
            self.clear()
        self.render_controls()

    def enter_host_mode(self) -> None:
        """Put the original Launchpad Pro into host-controlled LED mode."""

        self._send_sysex([0, 32, 41, 2, 16, 33, 0])
        self._send_sysex([0, 32, 41, 2, 16, 34, 0])

    def clear(self) -> None:
        self._send_control_change(0, self.palette.OFF)

    def render_state(self, state: AgentState) -> None:
        color = self.palette.STATE_COLORS[state]
        for note in self.layout.status_pads:
            self._send_note_on(note, color)

    def render_controls(self) -> None:
        self._send_note_on(self.layout.approve, self.palette.DIM_GREEN)
        self._send_note_on(self.layout.reject, self.palette.DIM_RED)
        self._send_note_on(self.layout.stop, self.palette.RED)
        self._send_note_on(self.layout.retry, self.palette.DIM_BLUE)

    def scroll_text(self, text: str, color: int, delay: float) -> None:
        columns = _text_columns(text)
        blank_columns = [0] * 8
        frames = blank_columns + columns + blank_columns

        for offset in range(len(frames) - 7):
            self.render_text_frame(frames[offset : offset + 8], color)
            time.sleep(delay)

    def render_text_frame(self, columns: list[int], color: int) -> None:
        for y in range(8):
            for x in range(8):
                lit = y > 0 and bool(columns[x] & (1 << (7 - y)))
                self._send_note_on(_grid_note(x, y), color if lit else self.palette.OFF)

    def poll_controls(self, on_action: Callable[[ControlAction], None]) -> None:
        if self.input_port is None:
            raise LaunchpadError("No Launchpad input port is open.")

        for message in self.input_port.iter_pending():
            action = self.action_from_message(message)
            if action is not None:
                on_action(action)

    def action_from_message(self, message: MidiMessage) -> ControlAction | None:
        if getattr(message, "type", "") != "note_on":
            return None
        if getattr(message, "velocity", 0) == 0:
            return None
        return self.layout.controls.get(getattr(message, "note", -1))

    def _send_note_on(self, note: int, velocity: int) -> None:
        self.output_port.send(
            self._message_factory("note_on", note=note, velocity=velocity)
        )

    def _send_control_change(self, control: int, value: int) -> None:
        self.output_port.send(
            self._message_factory("control_change", control=control, value=value)
        )

    def _send_sysex(self, data: list[int]) -> None:
        self.output_port.send(self._message_factory("sysex", data=data))


def list_midi_ports() -> tuple[list[str], list[str]]:
    mido = _import_mido()
    return list(mido.get_input_names()), list(mido.get_output_names())


def open_launchpad(
    *,
    input_name: str | None = None,
    output_name: str | None = None,
    layout: PadLayout | None = None,
    scroll_delay: float = 0.08,
) -> LaunchpadSurface:
    mido = _import_mido()
    selected_input = input_name or _pick_port(mido.get_input_names(), "input")
    selected_output = output_name or _pick_port(mido.get_output_names(), "output")

    return LaunchpadSurface(
        output_port=mido.open_output(selected_output),
        input_port=mido.open_input(selected_input),
        layout=layout,
        scroll_delay=scroll_delay,
    )


def run_surface(
    surface: LaunchpadSurface,
    state_source: Callable[[], AgentState],
    on_action: Callable[[ControlAction], None],
    *,
    poll_interval: float = 0.05,
) -> None:
    """Run the blocking render/input loop."""

    surface.initialize()
    last_state: AgentState | None = None

    try:
        while True:
            state = state_source()
            if state != last_state:
                surface.render_state(state)
                last_state = state
            surface.poll_controls(on_action)
            time.sleep(poll_interval)
    finally:
        surface.clear()


def _pick_port(names: list[str], direction: str) -> str:
    if not names:
        raise LaunchpadError(f"No MIDI {direction} ports found.")

    launchpad_names = [name for name in names if "launchpad" in name.lower()]
    live_names = [name for name in launchpad_names if "live port" in name.lower()]
    if live_names:
        return live_names[0]
    if launchpad_names:
        return launchpad_names[0]
    return names[0]


def _text_columns(text: str) -> list[int]:
    columns: list[int] = []
    for char in text.upper():
        glyph = FONT_5X7.get(char, FONT_5X7[" "])
        for x in range(5):
            value = 0
            for y, row in enumerate(glyph, start=1):
                if row[x] == "1":
                    value |= 1 << (7 - y)
            columns.append(value)
        columns.append(0)
    return columns


def _grid_note(x: int, y: int) -> int:
    return 81 + x - (10 * y)


def _message(message_type: str, **kwargs: int) -> MidiMessage:
    mido = _import_mido()
    return mido.Message(message_type, **kwargs)


def _import_mido() -> Any:
    try:
        import mido
    except ImportError as exc:
        raise LaunchpadError(
            "mido is not installed. Install this package with `pip install -e .`."
        ) from exc
    return mido
