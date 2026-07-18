"""Browser-test harness for the packaged live virtual surface."""

from __future__ import annotations

import signal
import threading
import time
from pathlib import Path

from pad_lattice.devices.base import ActionPressed, SessionIndicator, SurfaceView
from pad_lattice.events import AgentState, ControlAction
from pad_lattice.web_surface import WebSurface


def main() -> int:
    stopped = threading.Event()
    signal.signal(signal.SIGINT, lambda signum, frame: stopped.set())
    signal.signal(signal.SIGTERM, lambda signum, frame: stopped.set())
    root = Path(__file__).resolve().parents[1]
    surface = WebSurface(
        port=4174,
        asset_root=root / "src" / "pad_lattice" / "web_dist" / "play",
    )
    surface.initialize()
    surface.configure_lan("http://192.168.1.10:4174")
    surface.create_pairing()
    state = AgentState.WAITING_FOR_APPROVAL
    try:
        while not stopped.is_set():
            actions = (
                frozenset({ControlAction.APPROVE, ControlAction.REJECT})
                if state is AgentState.WAITING_FOR_APPROVAL
                else frozenset()
            )
            surface.render(
                SurfaceView(
                    state,
                    sessions=(
                        SessionIndicator(
                            slot=0,
                            state=state,
                            selected=True,
                            accent="cyan",
                            label="Reviewer",
                        ),
                    ),
                    available_actions=actions,
                )
            )
            for event in surface.poll_events():
                if isinstance(event, ActionPressed):
                    if event.action is ControlAction.APPROVE:
                        state = AgentState.SUCCESS
                    elif event.action is ControlAction.REJECT:
                        state = AgentState.CANCELLED
            stopped.wait(0.03)
    finally:
        surface.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
