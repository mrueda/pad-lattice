"""Generic static-palette MIDI grid control surface."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, TextIO

from pad_lattice.devices.base import (
    ActionPressed,
    SessionSelected,
    SurfaceEvent,
    SurfaceView,
)
from pad_lattice.devices.profiles import DeviceProfile, MidiAddress, MidiCommand
from pad_lattice.visual_protocol import VisualFrame, compile_visual_frame

MidiMessage = Any


class MidiDeviceError(RuntimeError):
    """Raised when MIDI hardware cannot be opened or driven."""


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
    "X": ("10001", "00000", "01010", "00100", "01010", "00000", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
}


class MidiGridSurface:
    """Render semantic Pad-Lattice views through a declarative MIDI profile."""

    def __init__(
        self,
        profile: DeviceProfile,
        output_port: Any,
        input_port: Any,
        *,
        input_name: str,
        output_name: str,
        message_factory: Callable[..., MidiMessage] | None = None,
        startup_greeting: str | None = "HELLO FROM CODEX CLI",
        scroll_delay: float = 0.08,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.profile = profile
        self.profile_id = profile.id
        self.input_name = input_name
        self.output_name = output_name
        self.selector_capacity = profile.selector_capacity
        self.accent_names = profile.accent_names
        self.visual_protocol = profile.visual_protocol
        self.output_port = output_port
        self.input_port = input_port
        self._message_factory = message_factory or _message
        self.startup_greeting = startup_greeting
        self.scroll_delay = scroll_delay
        self._sleep = sleeper
        self._closed = False
        self._address_values: dict[MidiAddress, int] = {}
        self._actions_by_address = {
            address: action for action, address in profile.controls.items()
        }
        self._selectors_by_address = {
            address: slot for slot, address in enumerate(profile.selectors)
        }

    def initialize(self) -> None:
        for command in self.profile.startup:
            self._send_command(command)
        self._address_values.clear()
        self.clear(force=True)
        if self.startup_greeting and self.profile.text_scroll:
            self.scroll_text(
                self.startup_greeting,
                self.profile.color("state:success:primary"),
                self.scroll_delay,
            )
            self.clear(force=True)

    def render(self, view: SurfaceView) -> None:
        self._render_frame(compile_visual_frame(view, self.selector_capacity))

    def poll_events(self) -> list[SurfaceEvent]:
        events: list[SurfaceEvent] = []
        for message in self.input_port.iter_pending():
            address = _address_from_input(message)
            if address is None:
                continue
            action = self._actions_by_address.get(address)
            if action is not None:
                events.append(ActionPressed(action))
                continue
            slot = self._selectors_by_address.get(address)
            if slot is not None:
                events.append(SessionSelected(slot))
        return events

    def clear(self, *, force: bool = False) -> None:
        if self.profile.clear:
            for command in self.profile.clear:
                self._send_command(command)
            self._address_values.clear()
            return

        addresses = {
            self.profile.grid_address(x, y)
            for y in range(self.profile.height)
            for x in range(self.profile.width)
        }
        addresses.update(self.profile.controls.values())
        addresses.update(self.profile.selectors)
        addresses.update(self.profile.statuses)
        if self.profile.overflow_indicator is not None:
            addresses.add(self.profile.overflow_indicator)
        for address in addresses:
            self._set_address(
                address,
                self.profile.color("off"),
                force=force,
            )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.clear(force=True)
        finally:
            try:
                for command in self.profile.shutdown:
                    self._send_command(command)
            finally:
                for port in (self.input_port, self.output_port):
                    close = getattr(port, "close", None)
                    if callable(close):
                        close()

    def scroll_text(self, text: str, color: int, delay: float) -> None:
        columns = _text_columns(text)
        blank_columns = [0] * self.profile.width
        frames = blank_columns + columns + blank_columns
        for offset in range(len(frames) - self.profile.width + 1):
            self._render_text_frame(frames[offset : offset + self.profile.width], color)
            self._sleep(delay)

    def _render_frame(self, frame: VisualFrame) -> None:
        region = self.profile.state_region
        for y, row in enumerate(frame.state):
            for x, token in enumerate(row):
                self._set_grid_pad(
                    region.x + x,
                    region.y + y,
                    self._resolve_color(token),
                )

        for index, address in enumerate(self.profile.selectors):
            self._set_address(address, self._resolve_color(frame.selectors[index]))
        for index, address in enumerate(self.profile.statuses):
            self._set_address(address, self._resolve_color(frame.statuses[index]))
        for action, address in self.profile.controls.items():
            self._set_address(address, self._resolve_color(frame.actions[action]))
        if self.profile.overflow_indicator is not None:
            self._set_address(
                self.profile.overflow_indicator,
                self._resolve_color(frame.overflow),
            )

    def _resolve_color(self, token: str) -> int:
        if not token.startswith("accent:"):
            return self.profile.color(token)
        _, name, role = token.split(":", 2)
        accent = self.profile.accent(name)
        return accent.selected if role == "selected" else accent.unselected

    def _render_text_frame(self, columns: list[int], color: int) -> None:
        for y in range(self.profile.height):
            for x in range(self.profile.width):
                lit = y > 0 and bool(columns[x] & (1 << (self.profile.height - 1 - y)))
                self._set_grid_pad(x, y, color if lit else self.profile.color("off"))

    def _set_grid_pad(self, x: int, y: int, color: int) -> None:
        self._set_address(self.profile.grid_address(x, y), color)

    def _set_address(
        self,
        address: MidiAddress,
        value: int,
        *,
        force: bool = False,
    ) -> None:
        if not force and self._address_values.get(address) == value:
            return
        if address.kind == "note":
            self.output_port.send(
                self._message_factory(
                    "note_on",
                    channel=address.channel,
                    note=address.number,
                    velocity=value,
                )
            )
        else:
            self.output_port.send(
                self._message_factory(
                    "control_change",
                    channel=address.channel,
                    control=address.number,
                    value=value,
                )
            )
        self._address_values[address] = value

    def _send_command(self, command: MidiCommand) -> None:
        if command.kind == "sysex":
            self.output_port.send(self._message_factory("sysex", data=list(command.data)))
        elif command.kind == "note":
            self.output_port.send(
                self._message_factory(
                    "note_on",
                    channel=command.channel,
                    note=command.number,
                    velocity=command.value,
                )
            )
        else:
            self.output_port.send(
                self._message_factory(
                    "control_change",
                    channel=command.channel,
                    control=command.number,
                    value=command.value,
                )
            )


def list_midi_ports() -> tuple[list[str], list[str]]:
    mido = _import_mido()
    return list(mido.get_input_names()), list(mido.get_output_names())


def monitor_midi_input(
    input_name: str | None,
    *,
    timeout: float | None = None,
    poll_interval: float = 0.01,
    output: TextIO | None = None,
) -> None:
    """Print incoming MIDI messages for profile discovery and debugging."""

    import sys

    mido = _import_mido()
    names = list(mido.get_input_names())
    if input_name is None:
        if len(names) != 1:
            raise MidiDeviceError(
                "Select an input with --input; available inputs: "
                + (", ".join(names) if names else "none")
            )
        input_name = names[0]

    stream = output or sys.stdout
    started = time.monotonic()
    with mido.open_input(input_name) as input_port:
        while timeout is None or time.monotonic() - started < timeout:
            for message in input_port.iter_pending():
                print(message, file=stream, flush=True)
            time.sleep(poll_interval)


def open_midi_grid_surface(
    profile: DeviceProfile,
    *,
    input_name: str,
    output_name: str,
    startup_greeting: str | None = "HELLO FROM CODEX CLI",
    scroll_delay: float = 0.08,
) -> MidiGridSurface:
    mido = _import_mido()
    try:
        output_port = mido.open_output(output_name)
    except Exception as exc:
        raise MidiDeviceError(f"could not open MIDI output {output_name!r}: {exc}") from exc
    try:
        input_port = mido.open_input(input_name)
    except Exception as exc:
        try:
            output_port.close()
        except Exception:
            pass
        raise MidiDeviceError(f"could not open MIDI input {input_name!r}: {exc}") from exc
    return MidiGridSurface(
        profile,
        output_port=output_port,
        input_port=input_port,
        input_name=input_name,
        output_name=output_name,
        startup_greeting=startup_greeting,
        scroll_delay=scroll_delay,
    )


def _address_from_input(message: MidiMessage) -> MidiAddress | None:
    message_type = getattr(message, "type", "")
    channel = getattr(message, "channel", 0)
    if message_type == "note_on" and getattr(message, "velocity", 0) > 0:
        return MidiAddress("note", getattr(message, "note", -1), channel)
    if message_type == "control_change" and getattr(message, "value", 0) > 0:
        return MidiAddress("cc", getattr(message, "control", -1), channel)
    return None


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


def _message(message_type: str, **kwargs: Any) -> MidiMessage:
    mido = _import_mido()
    return mido.Message(message_type, **kwargs)


def _import_mido() -> Any:
    try:
        import mido
    except ImportError as exc:
        raise MidiDeviceError(
            "MIDI support is unavailable. Install pad-lattice with its runtime dependencies."
        ) from exc
    return mido
