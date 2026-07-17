"""Declarative MIDI device profile loading, validation, and discovery."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Iterable

from pad_lattice.events import ControlAction

PROFILE_SCHEMA_VERSION = 1
SUPPORTED_DRIVERS = frozenset({"midi.palette-grid"})
PROFILE_STATUSES = frozenset({"supported", "experimental"})
REQUIRED_COLORS = frozenset(
    {
        "off",
        "white",
        "blue",
        "yellow",
        "green",
        "red",
        "dim_blue",
        "dim_green",
        "dim_red",
        "dim_yellow",
    }
)


class ProfileError(ValueError):
    """Raised when a device profile is missing or invalid."""


@dataclass(frozen=True)
class MidiAddress:
    kind: str
    number: int
    channel: int = 0


@dataclass(frozen=True)
class MidiCommand:
    kind: str
    channel: int = 0
    number: int | None = None
    value: int | None = None
    data: tuple[int, ...] = ()


@dataclass(frozen=True)
class AccentColors:
    bright: int
    dim: int


@dataclass(frozen=True)
class DeviceProfile:
    schema_version: int
    id: str
    name: str
    manufacturer: str
    family: str
    model: str
    status: str
    driver: str
    input_patterns: tuple[str, ...]
    output_patterns: tuple[str, ...]
    grid_kind: str
    grid_channel: int
    grid: tuple[tuple[int, ...], ...]
    state_rows: int
    controls: dict[ControlAction, MidiAddress]
    selectors: tuple[MidiAddress, ...]
    statuses: tuple[MidiAddress, ...]
    colors: dict[str, int]
    accents: tuple[AccentColors, ...]
    startup: tuple[MidiCommand, ...]
    clear: tuple[MidiCommand, ...]
    shutdown: tuple[MidiCommand, ...]
    text_scroll: bool
    source: str = ""

    @property
    def width(self) -> int:
        return len(self.grid[0])

    @property
    def height(self) -> int:
        return len(self.grid)

    @property
    def selector_capacity(self) -> int:
        return len(self.selectors)

    def grid_address(self, x: int, y: int) -> MidiAddress:
        return MidiAddress(self.grid_kind, self.grid[y][x], self.grid_channel)

    def color(self, name: str) -> int:
        try:
            return self.colors[name]
        except KeyError as exc:
            raise ProfileError(f"{self.id}: unknown color token: {name}") from exc


@dataclass(frozen=True)
class DeviceCandidate:
    profile: DeviceProfile
    input_name: str
    output_name: str


class ProfileCatalog:
    """Validated built-in and user-supplied device profiles."""

    def __init__(self, profiles: Iterable[DeviceProfile]) -> None:
        self._profiles: dict[str, DeviceProfile] = {}
        for profile in profiles:
            existing = self._profiles.get(profile.id)
            if existing is not None:
                raise ProfileError(
                    f"duplicate profile id {profile.id!r}: "
                    f"{existing.source} and {profile.source}"
                )
            self._profiles[profile.id] = profile

    @classmethod
    def load(cls, *, include_user: bool = True) -> "ProfileCatalog":
        profiles = list(_load_builtin_profiles())
        if include_user:
            for root in _profile_roots():
                profiles.extend(_load_path_profiles(root))
        return cls(profiles)

    @property
    def profiles(self) -> tuple[DeviceProfile, ...]:
        return tuple(self._profiles[key] for key in sorted(self._profiles))

    def get(self, profile_id: str) -> DeviceProfile:
        try:
            return self._profiles[profile_id]
        except KeyError as exc:
            raise ProfileError(f"unknown device profile: {profile_id}") from exc

    def detect(
        self,
        input_names: Iterable[str],
        output_names: Iterable[str],
        *,
        include_experimental: bool = True,
    ) -> tuple[DeviceCandidate, ...]:
        candidates: list[DeviceCandidate] = []
        for profile in self.profiles:
            if not include_experimental and profile.status != "supported":
                continue
            inputs = _matching_ports(input_names, profile.input_patterns)
            outputs = _matching_ports(output_names, profile.output_patterns)
            for input_name in inputs:
                for output_name in outputs:
                    candidates.append(DeviceCandidate(profile, input_name, output_name))
        return tuple(candidates)


def matching_ports(names: Iterable[str], patterns: tuple[str, ...]) -> tuple[str, ...]:
    """Return matches for the first profile pattern that matches any port."""

    return _matching_ports(names, patterns)


def load_profile_file(path: Path) -> DeviceProfile:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProfileError(f"profile file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ProfileError(f"{path}: invalid JSON: {exc.msg}") from exc
    return parse_profile(data, source=str(path))


def parse_profile(data: Any, *, source: str = "<profile>") -> DeviceProfile:
    if not isinstance(data, dict):
        raise ProfileError(f"{source}: top-level profile must be a JSON object")

    schema_version = _integer(data, "schema_version", source)
    if schema_version != PROFILE_SCHEMA_VERSION:
        raise ProfileError(
            f"{source}: unsupported schema_version {schema_version}; "
            f"expected {PROFILE_SCHEMA_VERSION}"
        )

    profile_id = _string(data, "id", source)
    if re.fullmatch(r"[a-z0-9][a-z0-9-]*(/[a-z0-9][a-z0-9-]*){2}", profile_id) is None:
        raise ProfileError(
            f"{source}: id must be manufacturer/family/model using lowercase slugs"
        )
    name = _string(data, "name", source)
    manufacturer = _string(data, "manufacturer", source)
    family = _string(data, "family", source)
    model = _string(data, "model", source)
    expected_id = "/".join(_slug(value) for value in (manufacturer, family, model))
    if profile_id != expected_id:
        raise ProfileError(
            f"{source}: id {profile_id!r} does not match profile metadata; "
            f"expected {expected_id!r}"
        )

    status = _string(data, "status", source)
    if status not in PROFILE_STATUSES:
        raise ProfileError(f"{source}: unsupported status: {status}")
    driver = _string(data, "driver", source)
    if driver not in SUPPORTED_DRIVERS:
        raise ProfileError(f"{source}: unknown driver: {driver}")

    ports = _object(data, "ports", source)
    input_patterns = _string_array(ports, "input", f"{source}.ports")
    output_patterns = _string_array(ports, "output", f"{source}.ports")
    _validate_patterns(input_patterns, f"{source}.ports.input")
    _validate_patterns(output_patterns, f"{source}.ports.output")

    grid_data = _object(data, "grid", source)
    grid_kind = _string(grid_data, "kind", f"{source}.grid")
    if grid_kind not in {"note", "cc"}:
        raise ProfileError(f"{source}.grid.kind must be 'note' or 'cc'")
    grid_channel = _midi_channel(grid_data.get("channel", 0), f"{source}.grid.channel")
    rows_data = grid_data.get("rows")
    if not isinstance(rows_data, list) or not rows_data:
        raise ProfileError(f"{source}.grid.rows must be a non-empty JSON array")
    rows: list[tuple[int, ...]] = []
    width: int | None = None
    for row_index, row_data in enumerate(rows_data):
        if not isinstance(row_data, list) or not row_data:
            raise ProfileError(f"{source}.grid.rows[{row_index}] must be an array")
        row = tuple(
            _midi_value(value, f"{source}.grid.rows[{row_index}][{column_index}]")
            for column_index, value in enumerate(row_data)
        )
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise ProfileError(f"{source}.grid.rows must all have the same width")
        rows.append(row)
    if width != 8 or len(rows) != 8:
        raise ProfileError(f"{source}.grid must be 8x8 for schema version 1")
    _validate_unique_addresses(
        [
            MidiAddress(grid_kind, number, grid_channel)
            for row in rows
            for number in row
        ],
        f"{source}.grid",
    )

    state_rows = grid_data.get("state_rows", 6)
    if not isinstance(state_rows, int) or isinstance(state_rows, bool) or not 1 <= state_rows <= 8:
        raise ProfileError(f"{source}.grid.state_rows must be an integer from 1 to 8")

    controls_data = _object(data, "controls", source)
    action_addresses: dict[ControlAction, MidiAddress] = {}
    for action in ControlAction:
        action_addresses[action] = _address(
            controls_data.get(action.value),
            f"{source}.controls.{action.value}",
        )
    selectors = _address_array(controls_data.get("selectors"), f"{source}.controls.selectors")
    statuses = _address_array(controls_data.get("statuses"), f"{source}.controls.statuses")
    if len(selectors) != len(statuses):
        raise ProfileError(f"{source}: selectors and statuses must have equal lengths")
    if not selectors:
        raise ProfileError(f"{source}: at least one selector/status pair is required")
    if len(selectors) > 8:
        raise ProfileError(f"{source}: at most eight selector slots are supported")
    _validate_unique_addresses(
        [*action_addresses.values(), *selectors, *statuses],
        f"{source}.controls",
    )

    colors_data = _object(data, "colors", source)
    colors = {
        key: _midi_value(value, f"{source}.colors.{key}")
        for key, value in colors_data.items()
    }
    missing_colors = sorted(REQUIRED_COLORS - colors.keys())
    if missing_colors:
        raise ProfileError(f"{source}: missing colors: {', '.join(missing_colors)}")

    accents_data = data.get("accents")
    if not isinstance(accents_data, list) or len(accents_data) != len(selectors):
        raise ProfileError(
            f"{source}.accents must provide exactly {len(selectors)} color pairs"
        )
    accents = tuple(
        AccentColors(
            bright=_midi_value(
                _object(value, "bright", f"{source}.accents[{index}]", value_is_object=True),
                f"{source}.accents[{index}].bright",
            ),
            dim=_midi_value(
                _object(value, "dim", f"{source}.accents[{index}]", value_is_object=True),
                f"{source}.accents[{index}].dim",
            ),
        )
        for index, value in enumerate(accents_data)
    )

    messages = data.get("messages", {})
    if not isinstance(messages, dict):
        raise ProfileError(f"{source}.messages must be a JSON object")

    capabilities = data.get("capabilities", {})
    if not isinstance(capabilities, dict):
        raise ProfileError(f"{source}.capabilities must be a JSON object")
    text_scroll = capabilities.get("text_scroll", True)
    if not isinstance(text_scroll, bool):
        raise ProfileError(f"{source}.capabilities.text_scroll must be boolean")

    return DeviceProfile(
        schema_version=schema_version,
        id=profile_id,
        name=name,
        manufacturer=manufacturer,
        family=family,
        model=model,
        status=status,
        driver=driver,
        input_patterns=input_patterns,
        output_patterns=output_patterns,
        grid_kind=grid_kind,
        grid_channel=grid_channel,
        grid=tuple(rows),
        state_rows=state_rows,
        controls=action_addresses,
        selectors=selectors,
        statuses=statuses,
        colors=colors,
        accents=accents,
        startup=_commands(messages.get("startup", []), f"{source}.messages.startup"),
        clear=_commands(messages.get("clear", []), f"{source}.messages.clear"),
        shutdown=_commands(messages.get("shutdown", []), f"{source}.messages.shutdown"),
        text_scroll=text_scroll,
        source=source,
    )


def _load_builtin_profiles() -> Iterable[DeviceProfile]:
    root = resources.files("pad_lattice").joinpath("device_profiles")
    for item in _walk_resources(root):
        if item.name.endswith(".json"):
            try:
                data = json.loads(item.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise ProfileError(f"{item}: invalid JSON: {exc.msg}") from exc
            yield parse_profile(data, source=str(item))


def _walk_resources(root: Any) -> Iterable[Any]:
    if not root.is_dir():
        return
    for item in root.iterdir():
        if item.is_dir():
            yield from _walk_resources(item)
        else:
            yield item


def _profile_roots() -> tuple[Path, ...]:
    roots: list[Path] = []
    config_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(config_home).expanduser() if config_home else Path.home() / ".config"
    roots.append(base / "pad-lattice" / "profiles")
    if profile_path := os.environ.get("PAD_LATTICE_PROFILE_PATH"):
        roots.extend(Path(value).expanduser() for value in profile_path.split(os.pathsep) if value)
    return tuple(roots)


def _load_path_profiles(root: Path) -> list[DeviceProfile]:
    if not root.is_dir():
        return []
    return [load_profile_file(path) for path in sorted(root.rglob("*.json"))]


def _matching_ports(names: Iterable[str], patterns: tuple[str, ...]) -> tuple[str, ...]:
    available = tuple(names)
    for pattern in patterns:
        matches = tuple(name for name in available if re.search(pattern, name, re.IGNORECASE))
        if matches:
            return matches
    return ()


def _validate_patterns(patterns: tuple[str, ...], location: str) -> None:
    for index, pattern in enumerate(patterns):
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ProfileError(f"{location}[{index}]: invalid regular expression: {exc}") from exc


def _object(
    data: dict[str, Any] | Any,
    key: str,
    location: str,
    *,
    value_is_object: bool = False,
) -> Any:
    if value_is_object:
        if not isinstance(data, dict):
            raise ProfileError(f"{location} must be a JSON object")
        if key not in data:
            raise ProfileError(f"{location}.{key} is required")
        return data[key]
    value = data.get(key)
    if not isinstance(value, dict):
        raise ProfileError(f"{location}.{key} must be a JSON object")
    return value


def _string(data: dict[str, Any], key: str, location: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ProfileError(f"{location}.{key} must be a non-empty string")
    return value


def _integer(data: dict[str, Any], key: str, location: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ProfileError(f"{location}.{key} must be an integer")
    return value


def _string_array(data: dict[str, Any], key: str, location: str) -> tuple[str, ...]:
    value = data.get(key)
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item for item in value)
    ):
        raise ProfileError(f"{location}.{key} must be a non-empty string array")
    return tuple(value)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _midi_value(value: Any, location: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 127:
        raise ProfileError(f"{location} must be an integer from 0 to 127")
    return value


def _midi_channel(value: Any, location: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 15:
        raise ProfileError(f"{location} must be an integer from 0 to 15")
    return value


def _address(value: Any, location: str) -> MidiAddress:
    if not isinstance(value, dict):
        raise ProfileError(f"{location} must be a JSON object")
    kind = value.get("kind")
    if kind not in {"note", "cc"}:
        raise ProfileError(f"{location}.kind must be 'note' or 'cc'")
    return MidiAddress(
        kind=kind,
        number=_midi_value(value.get("number"), f"{location}.number"),
        channel=_midi_channel(value.get("channel", 0), f"{location}.channel"),
    )


def _address_array(value: Any, location: str) -> tuple[MidiAddress, ...]:
    if not isinstance(value, list):
        raise ProfileError(f"{location} must be a JSON array")
    return tuple(_address(item, f"{location}[{index}]") for index, item in enumerate(value))


def _validate_unique_addresses(addresses: list[MidiAddress], location: str) -> None:
    seen: set[MidiAddress] = set()
    for address in addresses:
        if address in seen:
            raise ProfileError(f"{location}: duplicate MIDI address: {address}")
        seen.add(address)


def _commands(value: Any, location: str) -> tuple[MidiCommand, ...]:
    if not isinstance(value, list):
        raise ProfileError(f"{location} must be a JSON array")
    commands: list[MidiCommand] = []
    for index, item in enumerate(value):
        command_location = f"{location}[{index}]"
        if not isinstance(item, dict):
            raise ProfileError(f"{command_location} must be a JSON object")
        kind = item.get("type")
        if kind == "sysex":
            data = item.get("data")
            if not isinstance(data, list):
                raise ProfileError(f"{command_location}.data must be a JSON array")
            commands.append(
                MidiCommand(
                    kind="sysex",
                    data=tuple(
                        _midi_value(byte, f"{command_location}.data[{byte_index}]")
                        for byte_index, byte in enumerate(data)
                    ),
                )
            )
            continue
        if kind not in {"note", "cc"}:
            raise ProfileError(f"{command_location}.type must be 'sysex', 'note', or 'cc'")
        commands.append(
            MidiCommand(
                kind=kind,
                channel=_midi_channel(item.get("channel", 0), f"{command_location}.channel"),
                number=_midi_value(item.get("number"), f"{command_location}.number"),
                value=_midi_value(item.get("value"), f"{command_location}.value"),
            )
        )
    return tuple(commands)
