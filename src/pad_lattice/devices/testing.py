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
from pad_lattice.devices.base import (
    ActionPressed,
    ControlSurface,
    SessionIndicator,
    SessionSelected,
    SurfaceView,
)
from pad_lattice.devices.profiles import DeviceProfile
from pad_lattice.events import AgentState, ControlAction

VISUAL_STATES: tuple[tuple[AgentState, str], ...] = (
    (AgentState.RUNNING, "steady blue ellipsis"),
    (AgentState.WAITING_FOR_REPLY, "white question mark"),
    (AgentState.USER_TYPING, "cyan chevron"),
    (AgentState.WAITING_FOR_APPROVAL, "restrained amber exclamation mark"),
    (AgentState.SUCCESS, "green happy face"),
    (AgentState.ERROR, "red X"),
    (AgentState.CANCELLED, "gray hollow square"),
)


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

    visual_checks = {
        **{state.value: False for state, _ in VISUAL_STATES},
        "idle": False,
        "overflow": False,
    }
    action_checks = {action.value: False for action in ControlAction}
    selector_checks = {
        str(slot + 1): False for slot in range(surface.selector_capacity)
    }
    completed = False
    stage = "initialize"
    failure: BaseException | None = None

    try:
        surface.initialize()
        stage = "visual"
        surface.render(SurfaceView(selected_state=None))
        time.sleep(settle_delay)
        visual_checks["idle"] = _confirm(
            "Do you see a dim three-pad idle dash? [y/N] ",
            input_stream,
            output_stream,
        )
        for state, description in VISUAL_STATES:
            surface.render(
                SurfaceView(
                    selected_state=state,
                    available_actions=frozenset(ControlAction),
                )
            )
            time.sleep(settle_delay)
            visual_checks[state.value] = _confirm(
                f"Do you see a {description}? [y/N] ",
                input_stream,
                output_stream,
            )
        surface.render(
            SurfaceView(
                selected_state=AgentState.WAITING_FOR_REPLY,
                overflow_count=1,
            )
        )
        time.sleep(settle_delay)
        visual_checks["overflow"] = _confirm(
            "Do you see one steady amber overflow indicator? [y/N] ",
            input_stream,
            output_stream,
        )

        stage = "actions"
        surface.render(
            SurfaceView(
                selected_state=AgentState.WAITING_FOR_REPLY,
                available_actions=frozenset(ControlAction),
            )
        )
        for action in ControlAction:
            print(
                f"Press the {action.value.upper()} control.",
                file=output_stream,
                flush=True,
            )
            action_checks[action.value] = _wait_for_event(
                surface,
                ActionPressed(action),
                event_timeout,
            )

        stage = "selectors"
        indicators = tuple(
            SessionIndicator(
                slot=slot,
                state=VISUAL_STATES[slot % len(VISUAL_STATES)][0],
                accent=surface.accent_names[slot],
            )
            for slot in range(surface.selector_capacity)
        )
        for slot in range(surface.selector_capacity):
            surface.render(
                SurfaceView(
                    selected_state=AgentState.WAITING_FOR_REPLY,
                    sessions=tuple(
                        SessionIndicator(
                            slot=indicator.slot,
                            state=indicator.state,
                            selected=indicator.slot == slot,
                            accent=indicator.accent,
                        )
                        for indicator in indicators
                    ),
                    available_actions=frozenset(ControlAction),
                )
            )
            print(
                f"Press agent selector {slot + 1}.",
                file=output_stream,
                flush=True,
            )
            selector_checks[str(slot + 1)] = _wait_for_event(
                surface,
                SessionSelected(slot),
                event_timeout,
            )
        completed = True
    except BaseException as exc:
        failure = exc
    finally:
        try:
            surface.close()
        except BaseException as exc:
            stage = "close"
            if failure is None:
                failure = exc

        report = _profile_test_report(
            surface,
            profile,
            completed=completed,
            failure_stage=None if failure is None else stage,
            visual_checks=visual_checks,
            action_checks=action_checks,
            selector_checks=selector_checks,
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if failure is not None:
        raise failure
    return report


def _confirm(prompt: str, input_stream: TextIO, output_stream: TextIO) -> bool:
    print(prompt, end="", file=output_stream, flush=True)
    return input_stream.readline().strip().lower() in {"y", "yes"}


def _wait_for_event(
    surface: ControlSurface,
    expected: ActionPressed | SessionSelected,
    timeout: float,
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if expected in surface.poll_events():
            return True
        time.sleep(0.01)
    return False


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
