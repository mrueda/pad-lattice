"""Declarative MIDI device profile loading, validation, and discovery."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Iterable

from pad_lattice.events import AgentState, ControlAction
from pad_lattice.visual_protocol import (
    STATE_HEIGHT,
    STATE_WIDTH,
    VISUAL_PROTOCOL_VERSION,
)

PROFILE_SCHEMA_VERSION = 1
SUPPORTED_DRIVERS = frozenset({"midi.palette-grid"})
PROFILE_STATUSES = frozenset({"supported", "experimental"})
CONFORMANCE_LEVELS = frozenset({"core-state", "multi-agent", "actions"})


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
    name: str
    selected: int
    unselected: int


@dataclass(frozen=True)
class GridRegion:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class DeviceProfile:
    schema_version: int
    visual_protocol: str
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
    state_region: GridRegion
    controls: dict[ControlAction, MidiAddress]
    selectors: tuple[MidiAddress, ...]
    statuses: tuple[MidiAddress, ...]
    overflow_indicator: MidiAddress | None
    palette: dict[str, int]
    accents: tuple[AccentColors, ...]
    conformance: frozenset[str]
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

    @property
    def accent_names(self) -> tuple[str, ...]:
        return tuple(accent.name for accent in self.accents)

    def grid_address(self, x: int, y: int) -> MidiAddress:
        return MidiAddress(self.grid_kind, self.grid[y][x], self.grid_channel)

    def color(self, name: str) -> int:
        try:
            return self.palette[name]
        except KeyError as exc:
            raise ProfileError(f"{self.id}: unknown color token: {name}") from exc

    def accent(self, name: str) -> AccentColors:
        for accent in self.accents:
            if accent.name == name:
                return accent
        raise ProfileError(f"{self.id}: unknown session accent: {name}")


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
    visual_protocol = _string(data, "visual_protocol", source)
    if visual_protocol != VISUAL_PROTOCOL_VERSION:
        raise ProfileError(
            f"{source}: unsupported visual_protocol {visual_protocol!r}; "
            f"expected {VISUAL_PROTOCOL_VERSION!r}"
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
        raise ProfileError(f"{source}.grid must be 8x8")
    _validate_unique_addresses(
        [
            MidiAddress(grid_kind, number, grid_channel)
            for row in rows
            for number in row
        ],
        f"{source}.grid",
    )

    surface_data = _object(data, "surface", source)
    region_data = _object(surface_data, "state_region", f"{source}.surface")
    state_region = GridRegion(
        x=_bounded_integer(region_data.get("x"), f"{source}.surface.state_region.x", 0, 7),
        y=_bounded_integer(region_data.get("y"), f"{source}.surface.state_region.y", 0, 7),
        width=_bounded_integer(
            region_data.get("width"),
            f"{source}.surface.state_region.width",
            1,
            8,
        ),
        height=_bounded_integer(
            region_data.get("height"),
            f"{source}.surface.state_region.height",
            1,
            8,
        ),
    )
    if state_region.width != STATE_WIDTH or state_region.height != STATE_HEIGHT:
        raise ProfileError(
            f"{source}.surface.state_region must be {STATE_WIDTH}x{STATE_HEIGHT} "
            f"for Visual Protocol {VISUAL_PROTOCOL_VERSION}"
        )
    if (
        state_region.x + state_region.width > width
        or state_region.y + state_region.height > len(rows)
    ):
        raise ProfileError(f"{source}.surface.state_region exceeds the grid")

    controls_data = surface_data.get("actions", {})
    if not isinstance(controls_data, dict):
        raise ProfileError(f"{source}.surface.actions must be a JSON object")
    unknown_actions = sorted(set(controls_data) - {action.value for action in ControlAction})
    if unknown_actions:
        raise ProfileError(
            f"{source}.surface.actions contains unknown actions: "
            + ", ".join(unknown_actions)
        )
    action_addresses: dict[ControlAction, MidiAddress] = {}
    for action in ControlAction:
        if action.value in controls_data:
            action_addresses[action] = _address(
                controls_data[action.value],
                f"{source}.surface.actions.{action.value}",
            )
    selectors = _address_array(
        surface_data.get("agent_selectors"),
        f"{source}.surface.agent_selectors",
    )
    statuses = _address_array(
        surface_data.get("agent_statuses"),
        f"{source}.surface.agent_statuses",
    )
    if len(selectors) != len(statuses):
        raise ProfileError(f"{source}: selectors and statuses must have equal lengths")
    if not selectors:
        raise ProfileError(f"{source}: at least one selector/status pair is required")
    if len(selectors) > 8:
        raise ProfileError(f"{source}: at most eight selector slots are supported")
    indicators_data = surface_data.get("indicators", {})
    if not isinstance(indicators_data, dict):
        raise ProfileError(f"{source}.surface.indicators must be a JSON object")
    unknown_indicators = sorted(set(indicators_data) - {"overflow"})
    if unknown_indicators:
        raise ProfileError(
            f"{source}.surface.indicators contains unknown indicators: "
            + ", ".join(unknown_indicators)
        )
    overflow_indicator = (
        _address(
            indicators_data["overflow"],
            f"{source}.surface.indicators.overflow",
        )
        if "overflow" in indicators_data
        else None
    )
    surface_addresses = [*action_addresses.values(), *selectors, *statuses]
    if overflow_indicator is not None:
        surface_addresses.append(overflow_indicator)
    _validate_unique_addresses(surface_addresses, f"{source}.surface")

    state_addresses = {
        MidiAddress(grid_kind, rows[y][x], grid_channel)
        for y in range(state_region.y, state_region.y + state_region.height)
        for x in range(state_region.x, state_region.x + state_region.width)
    }
    overlap = state_addresses.intersection(surface_addresses)
    if overlap:
        raise ProfileError(
            f"{source}.surface: state region overlaps a control address: "
            f"{sorted(overlap, key=lambda item: (item.kind, item.channel, item.number))[0]}"
        )

    palette = _palette(_object(data, "palette", source), f"{source}.palette")

    accents_data = data.get("accents")
    if not isinstance(accents_data, list) or len(accents_data) != len(selectors):
        raise ProfileError(
            f"{source}.accents must provide exactly {len(selectors)} named color pairs"
        )
    accents_list: list[AccentColors] = []
    for index, value in enumerate(accents_data):
        location = f"{source}.accents[{index}]"
        if not isinstance(value, dict):
            raise ProfileError(f"{location} must be a JSON object")
        accent_name = _string(value, "name", location)
        if re.fullmatch(r"[a-z][a-z0-9-]*", accent_name) is None:
            raise ProfileError(f"{location}.name must be a lowercase slug")
        accents_list.append(
            AccentColors(
                name=accent_name,
                selected=_midi_value(value.get("selected"), f"{location}.selected"),
                unselected=_midi_value(
                    value.get("unselected"),
                    f"{location}.unselected",
                ),
            )
        )
    accents = tuple(accents_list)
    accent_names = [accent.name for accent in accents]
    if len(set(accent_names)) != len(accent_names):
        raise ProfileError(f"{source}.accents must use unique names")

    conformance_data = data.get("conformance")
    if (
        not isinstance(conformance_data, list)
        or not conformance_data
        or not all(isinstance(item, str) for item in conformance_data)
    ):
        raise ProfileError(f"{source}.conformance must be a non-empty string array")
    conformance = frozenset(conformance_data)
    unknown_conformance = sorted(conformance - CONFORMANCE_LEVELS)
    if unknown_conformance:
        raise ProfileError(
            f"{source}.conformance contains unknown levels: "
            + ", ".join(unknown_conformance)
        )
    if "core-state" not in conformance:
        raise ProfileError(f"{source}.conformance must include core-state")
    if "multi-agent" in conformance and len(selectors) < 2:
        raise ProfileError(
            f"{source}: multi-agent conformance requires at least two selector slots"
        )
    if "multi-agent" in conformance and overflow_indicator is None:
        raise ProfileError(
            f"{source}: multi-agent conformance requires an overflow indicator"
        )
    if "actions" in conformance:
        missing_actions = [
            action.value for action in ControlAction if action not in action_addresses
        ]
        if missing_actions:
            raise ProfileError(
                f"{source}: actions conformance requires mappings for: "
                + ", ".join(missing_actions)
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
        visual_protocol=visual_protocol,
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
        state_region=state_region,
        controls=action_addresses,
        selectors=selectors,
        statuses=statuses,
        overflow_indicator=overflow_indicator,
        palette=palette,
        accents=accents,
        conformance=conformance,
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
    data: dict[str, Any],
    key: str,
    location: str,
) -> Any:
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


def _bounded_integer(value: Any, location: str, minimum: int, maximum: int) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or not minimum <= value <= maximum
    ):
        raise ProfileError(
            f"{location} must be an integer from {minimum} to {maximum}"
        )
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


def _palette(data: dict[str, Any], location: str) -> dict[str, int]:
    allowed_keys = {"off", "idle", "activity", "states", "actions", "system"}
    unknown_keys = sorted(set(data) - allowed_keys)
    if unknown_keys:
        raise ProfileError(
            f"{location} contains unknown sections: " + ", ".join(unknown_keys)
        )

    palette = {
        token: _midi_value(data.get(token), f"{location}.{token}")
        for token in ("off", "idle", "activity")
    }

    states = _object(data, "states", location)
    unknown_states = sorted(set(states) - {state.value for state in AgentState})
    if unknown_states:
        raise ProfileError(
            f"{location}.states contains unknown states: " + ", ".join(unknown_states)
        )
    for state in AgentState:
        state_data = _object(states, state.value, f"{location}.states")
        for role in ("primary", "summary"):
            palette[f"state:{state.value}:{role}"] = _midi_value(
                state_data.get(role),
                f"{location}.states.{state.value}.{role}",
            )

    actions = _object(data, "actions", location)
    unknown_actions = sorted(set(actions) - {action.value for action in ControlAction})
    if unknown_actions:
        raise ProfileError(
            f"{location}.actions contains unknown actions: "
            + ", ".join(unknown_actions)
        )
    for action in ControlAction:
        action_data = _object(actions, action.value, f"{location}.actions")
        palette[f"action:{action.value}:enabled"] = _midi_value(
            action_data.get("enabled"),
            f"{location}.actions.{action.value}.enabled",
        )

    system = _object(data, "system", location)
    palette["system:overflow"] = _midi_value(
        system.get("overflow"),
        f"{location}.system.overflow",
    )
    return palette


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
