"""Resolve profile/port selections and open physical control surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pad_lattice.devices.midi_grid import (
    MidiGridSurface,
    list_midi_ports,
    open_midi_grid_surface,
)
from pad_lattice.devices.profiles import (
    DeviceCandidate,
    DeviceProfile,
    ProfileCatalog,
    ProfileError,
    load_profile_file,
    matching_ports,
)


@dataclass(frozen=True)
class ResolvedDevice:
    profile: DeviceProfile
    input_name: str
    output_name: str


def resolve_device(
    *,
    profile_id: str | None = None,
    profile_file: Path | None = None,
    input_name: str | None = None,
    output_name: str | None = None,
    catalog: ProfileCatalog | None = None,
    input_names: list[str] | None = None,
    output_names: list[str] | None = None,
) -> ResolvedDevice:
    if profile_id and profile_file:
        raise ProfileError("use either --profile or --profile-file, not both")

    scan_inputs = input_names is None and input_name is None
    scan_outputs = output_names is None and output_name is None
    detected_inputs: list[str] = []
    detected_outputs: list[str] = []
    if scan_inputs or scan_outputs:
        detected_inputs, detected_outputs = list_midi_ports()
    input_names = detected_inputs if input_names is None else input_names
    output_names = detected_outputs if output_names is None else output_names

    if profile_file is not None:
        profile = load_profile_file(profile_file)
        return _resolve_profile_ports(
            profile,
            input_names,
            output_names,
            input_name=input_name,
            output_name=output_name,
        )

    selected_catalog = catalog or ProfileCatalog.load()
    if profile_id is not None:
        profile = selected_catalog.get(profile_id)
        return _resolve_profile_ports(
            profile,
            input_names,
            output_names,
            input_name=input_name,
            output_name=output_name,
        )

    candidate_inputs = [input_name] if input_name else input_names
    candidate_outputs = [output_name] if output_name else output_names
    supported = selected_catalog.detect(
        candidate_inputs,
        candidate_outputs,
        include_experimental=False,
    )
    if len(supported) == 1:
        candidate = supported[0]
        return ResolvedDevice(candidate.profile, candidate.input_name, candidate.output_name)
    if len(supported) > 1:
        raise ProfileError(_ambiguous_message(supported))

    experimental = tuple(
        candidate
        for candidate in selected_catalog.detect(candidate_inputs, candidate_outputs)
        if candidate.profile.status == "experimental"
    )
    if experimental:
        ids = ", ".join(sorted({candidate.profile.id for candidate in experimental}))
        raise ProfileError(
            f"only experimental device profiles matched ({ids}); "
            "select one explicitly with --profile"
        )
    raise ProfileError(
        "no supported MIDI device profile matched; run `pad-lattice devices` or pass --profile"
    )


def open_resolved_surface(
    device: ResolvedDevice,
    *,
    startup_greeting: str | None,
    scroll_delay: float,
) -> MidiGridSurface:
    if device.profile.driver != "midi.palette-grid":
        raise ProfileError(f"unsupported driver: {device.profile.driver}")
    return open_midi_grid_surface(
        device.profile,
        input_name=device.input_name,
        output_name=device.output_name,
        startup_greeting=startup_greeting,
        scroll_delay=scroll_delay,
    )


def discover_devices(
    *,
    catalog: ProfileCatalog | None = None,
    input_names: list[str] | None = None,
    output_names: list[str] | None = None,
) -> tuple[DeviceCandidate, ...]:
    selected_catalog = catalog or ProfileCatalog.load()
    if input_names is None or output_names is None:
        detected_inputs, detected_outputs = list_midi_ports()
        input_names = detected_inputs if input_names is None else input_names
        output_names = detected_outputs if output_names is None else output_names
    return selected_catalog.detect(input_names, output_names)


def _resolve_profile_ports(
    profile: DeviceProfile,
    input_names: list[str],
    output_names: list[str],
    *,
    input_name: str | None,
    output_name: str | None,
) -> ResolvedDevice:
    inputs = (input_name,) if input_name else matching_ports(input_names, profile.input_patterns)
    outputs = (
        (output_name,)
        if output_name
        else matching_ports(output_names, profile.output_patterns)
    )
    if not inputs:
        raise ProfileError(f"no MIDI input matched profile {profile.id}")
    if not outputs:
        raise ProfileError(f"no MIDI output matched profile {profile.id}")
    if len(inputs) != 1 or len(outputs) != 1:
        candidates = tuple(
            DeviceCandidate(profile, candidate_input, candidate_output)
            for candidate_input in inputs
            for candidate_output in outputs
        )
        raise ProfileError(_ambiguous_message(candidates))
    return ResolvedDevice(profile, inputs[0], outputs[0])


def _ambiguous_message(candidates: tuple[DeviceCandidate, ...]) -> str:
    details = "; ".join(
        f"{candidate.profile.id}: input={candidate.input_name!r}, output={candidate.output_name!r}"
        for candidate in candidates
    )
    return (
        "multiple MIDI device candidates matched; pass --profile, --input, "
        f"and --output ({details})"
    )
