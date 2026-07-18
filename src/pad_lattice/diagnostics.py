"""Privacy-safe installation diagnostics."""

from __future__ import annotations

import os
import platform
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from pad_lattice import __version__
from pad_lattice.codex_hooks import (
    HOOK_EVENTS,
    default_codex_hooks_path,
    installed_codex_hook_events,
)
from pad_lattice.devices.midi_grid import list_midi_ports
from pad_lattice.devices.profiles import ProfileCatalog, ProfileError
from pad_lattice.protocol import (
    ProtocolError,
    default_socket_path,
    request_message,
    status_message,
)


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    status: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


def collect_diagnostics(
    *,
    socket_path: str | None = None,
    hooks_path: Path | None = None,
) -> dict[str, Any]:
    """Inspect local setup without opening a MIDI device for exclusive use."""

    socket_path = socket_path or default_socket_path()
    hooks_path = hooks_path or default_codex_hooks_path()
    checks = [
        DiagnosticCheck(
            "runtime",
            "ok",
            f"Pad-Lattice {__version__} on Python {platform.python_version()}",
            {"platform": platform.platform()},
        )
    ]

    catalog: ProfileCatalog | None = None
    try:
        catalog = ProfileCatalog.load()
        checks.append(
            DiagnosticCheck(
                "profiles",
                "ok",
                f"{len(catalog.profiles)} device profiles loaded",
                {
                    "profiles": [
                        {"id": profile.id, "status": profile.status}
                        for profile in catalog.profiles
                    ]
                },
            )
        )
    except (OSError, ProfileError, ValueError) as exc:
        checks.append(DiagnosticCheck("profiles", "error", _redact_text(str(exc))))

    inputs: list[str] = []
    outputs: list[str] = []
    try:
        inputs, outputs = list_midi_ports()
        port_status = "ok" if inputs and outputs else "warning"
        summary = (
            f"{len(inputs)} input and {len(outputs)} output MIDI ports found"
            if inputs or outputs
            else "no MIDI ports found"
        )
        checks.append(
            DiagnosticCheck(
                "midi",
                port_status,
                summary,
                {"inputs": inputs, "outputs": outputs},
            )
        )
    except Exception as exc:
        checks.append(DiagnosticCheck("midi", "error", _redact_text(str(exc))))

    if catalog is not None:
        candidates = catalog.detect(inputs, outputs)
        checks.append(
            DiagnosticCheck(
                "devices",
                "ok" if candidates else "warning",
                (
                    f"{len(candidates)} profile/port match"
                    + ("es" if len(candidates) != 1 else "")
                    if candidates
                    else "no device profile matches the available ports"
                ),
                {
                    "matches": [
                        {
                            "profile": candidate.profile.id,
                            "status": candidate.profile.status,
                            "input": candidate.input_name,
                            "output": candidate.output_name,
                        }
                        for candidate in candidates
                    ]
                },
            )
        )

    try:
        status_payload = request_message(socket_path, status_message())
        if status_payload.get("type") != "status":
            raise ProtocolError(
                f"unexpected daemon response: {status_payload.get('type')!r}"
            )
        socket_mode = _socket_mode(socket_path)
        secure = socket_mode in {None, "0600"}
        checks.append(
            DiagnosticCheck(
                "daemon",
                "ok" if secure else "warning",
                (
                    f"daemon reachable with profile {status_payload.get('profile')}"
                    if secure
                    else f"daemon reachable, but socket mode is {socket_mode}"
                ),
                {
                    "socket": _redact_path(socket_path),
                    "socket_mode": socket_mode,
                    "profile": status_payload.get("profile"),
                    "sessions": len(status_payload.get("sessions", [])),
                },
            )
        )
    except (ConnectionError, FileNotFoundError, OSError, ProtocolError) as exc:
        checks.append(
            DiagnosticCheck(
                "daemon",
                "warning",
                "daemon is not reachable",
                {
                    "socket": _redact_path(socket_path),
                    "error": _redact_text(str(exc)),
                },
            )
        )

    try:
        installed_events = installed_codex_hook_events(hooks_path)
        complete = set(installed_events) == set(HOOK_EVENTS)
        checks.append(
            DiagnosticCheck(
                "codex_hooks",
                "ok" if complete else "warning",
                (
                    "all Pad-Lattice lifecycle hooks are installed"
                    if complete
                    else f"{len(installed_events)} of {len(HOOK_EVENTS)} hooks installed"
                ),
                {
                    "path": _redact_path(hooks_path),
                    "events": list(installed_events),
                },
            )
        )
    except (OSError, ValueError) as exc:
        checks.append(
            DiagnosticCheck(
                "codex_hooks",
                "error",
                _redact_text(str(exc)),
                {"path": _redact_path(hooks_path)},
            )
        )

    overall = "ok"
    statuses = {check.status for check in checks}
    if "error" in statuses:
        overall = "error"
    elif "warning" in statuses:
        overall = "warning"
    return {
        "version": __version__,
        "overall": overall,
        "checks": [asdict(check) for check in checks],
    }


def print_diagnostics(report: dict[str, Any]) -> None:
    print(f"Pad-Lattice doctor {report.get('version')}")
    for check in report.get("checks", []):
        if not isinstance(check, dict):
            continue
        status = str(check.get("status", "error")).upper()
        print(f"[{status:<7}] {check.get('name')}: {check.get('summary')}")
    print(f"Overall: {str(report.get('overall', 'error')).upper()}")


def diagnostics_exit_code(report: dict[str, Any]) -> int:
    return 1 if report.get("overall") == "error" else 0


def _socket_mode(socket_path: str) -> str | None:
    try:
        mode = os.stat(socket_path).st_mode
    except FileNotFoundError:
        return None
    return format(mode & 0o7777, "04o")


def _redact_path(path: str | Path) -> str:
    return _redact_text(str(path))


def _redact_text(value: str) -> str:
    replacements = [(str(Path.home()), "~")]
    if runtime_dir := os.environ.get("XDG_RUNTIME_DIR"):
        replacements.append((runtime_dir, "$XDG_RUNTIME_DIR"))
    for local_path, display_path in sorted(
        replacements,
        key=lambda replacement: len(replacement[0]),
        reverse=True,
    ):
        if local_path:
            value = value.replace(local_path, display_path)
    return value
