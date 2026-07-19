"""Standalone runner for the shared multi-agent guided Demo."""

from __future__ import annotations

import time
from typing import TextIO

from pad_lattice.audio import AudioFeedback
from pad_lattice.devices.base import ControlSurface
from pad_lattice.events import ControlAction
from pad_lattice.experience_runtime import run_experience_loop


def run_demo_surface(
    surface: ControlSurface,
    *,
    poll_interval: float = 0.03,
    output: TextIO | None = None,
    audio_feedback: AudioFeedback | None = None,
    wait_for_request: bool = False,
    clock=time.monotonic,
    sleep=time.sleep,
) -> tuple[ControlAction, ...]:
    """Run the same deterministic Demo on physical and virtual surfaces."""

    controller = run_experience_loop(
        surface,
        "demo",
        poll_interval=poll_interval,
        output=output,
        audio_feedback=audio_feedback,
        wait_for_request=wait_for_request,
        clock=clock,
        sleep=sleep,
    )
    return tuple(
        event for event in controller.demo_actions if isinstance(event, ControlAction)
    )
