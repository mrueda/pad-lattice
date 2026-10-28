"""Interactive, privacy-preserving device profile verification."""

from __future__ import annotations

import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

from pad_lattice import __version__
from pad_lattice.devices.base import ControlSurface
from pad_lattice.devices.profiles import DeviceProfile
from pad_lattice.devices.test_run import ProfileTestRun


def run_profile_test(
    surface: ControlSurface,
    profile: DeviceProfile,
    report_path: Path,
    *,
    input_stream: TextIO = sys.stdin,
    output_stream: TextIO = sys.stdout,
    event_timeout: float = 15.0,
    settle_delay: float = 0.15,
) -> dict[str, Any]:
    """Exercise output and input mappings and write a sanitized JSON report."""
    run = ProfileTestRun(surface, profile, event_timeout=event_timeout)
    try:
        run.start()
        while run.active:
            step = run.step
            if step.expected is None:
                time.sleep(settle_delay)
                print(f"Do you see: {step.prompt}? [y/N] ", end="", file=output_stream, flush=True)
                run.answer(step.id, input_stream.readline().strip().lower() in {"y", "yes"})
            else:
                print(step.prompt, file=output_stream, flush=True)
                while run.active and run.step.id == step.id:
                    run.tick()
                    time.sleep(0.01)
    except BaseException:
        run.cancel("interrupted")
        raise
    finally:
        report = profile_test_report(run)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def profile_test_report(run: ProfileTestRun) -> dict[str, Any]:
    return _profile_test_report(
        run.surface, run.profile, completed=run.status == "completed",
        failure_stage=run.failure_stage, visual_checks=dict(run.checks["visual"]),
        action_checks=dict(run.checks["actions"]), selector_checks=dict(run.checks["selectors"]),
    )


def _profile_test_report(
    surface: ControlSurface,
    profile: DeviceProfile,
    *,
    completed: bool,
    failure_stage: str | None,
    visual_checks: dict[str, bool],
    action_checks: dict[str, bool],
    selector_checks: dict[str, bool],
) -> dict[str, Any]:
    passed = (
        completed
        and failure_stage is None
        and all(visual_checks.values())
        and all(action_checks.values())
        and all(selector_checks.values())
    )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pad_lattice_version": __version__,
        "device": {
            "profile_id": profile.id,
            "profile_status": profile.status,
            "visual_protocol": profile.visual_protocol,
            "conformance": sorted(profile.conformance),
            "input_port": surface.input_name,
            "output_port": surface.output_name,
        },
        "environment": {
            "system": platform.system(),
            "release": platform.release(),
            "python": platform.python_version(),
        },
        "results": {
            "completed": completed,
            "failure_stage": failure_stage,
            "visual": visual_checks,
            "actions": action_checks,
            "selectors": selector_checks,
        },
        "passed": passed,
    }
