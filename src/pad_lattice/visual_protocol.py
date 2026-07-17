"""Pad-Lattice Visual Protocol 0.1 logical frame compiler."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pad_lattice.events import AgentState, ControlAction

if TYPE_CHECKING:
    from pad_lattice.devices.base import SurfaceView

VISUAL_PROTOCOL_VERSION = "0.1"
STATE_WIDTH = 7
STATE_HEIGHT = 8
RUNNING_ACTIVITY_INTERVAL = 1.5

OFF = "off"
IDLE = "idle"
ACTIVITY = "activity"


@dataclass(frozen=True)
class VisualFrame:
    """Logical lights produced without knowledge of MIDI addresses or values."""

    state: tuple[tuple[str, ...], ...]
    selectors: tuple[str, ...]
    statuses: tuple[str, ...]
    actions: dict[ControlAction, str]
    overflow: str


STATE_GLYPHS: dict[AgentState, tuple[tuple[int, int], ...]] = {
    AgentState.RUNNING: tuple(
        (x, y)
        for x in (1, 3, 5)
        for y in (3, 4)
    ),
    AgentState.WAITING_FOR_REPLY: (
        (1, 0),
        (2, 0),
        (3, 0),
        (4, 0),
        (5, 0),
        (0, 1),
        (6, 1),
        (6, 2),
        (5, 2),
        (5, 3),
        (4, 3),
        (4, 4),
        (3, 5),
        (3, 7),
    ),
    AgentState.USER_TYPING: (
        (1, 1),
        (2, 2),
        (3, 3),
        (4, 4),
        (3, 5),
        (2, 6),
        (1, 7),
    ),
    AgentState.WAITING_FOR_APPROVAL: tuple(
        (3, y) for y in range(5)
    ) + ((3, 7),),
    AgentState.SUCCESS: (
        (1, 2),
        (5, 2),
        (0, 4),
        (1, 5),
        (2, 6),
        (3, 7),
        (4, 6),
        (5, 5),
        (6, 4),
    ),
    AgentState.ERROR: tuple(
        sorted(
            {
                *((y, y) for y in range(4)),
                *((6 - y, y) for y in range(4)),
                *((7 - y, y) for y in range(4, 8)),
                *((y - 1, y) for y in range(4, 8)),
            }
        )
    ),
    AgentState.CANCELLED: tuple(
        sorted(
            {
                *((x, 1) for x in range(1, 6)),
                *((x, 6) for x in range(1, 6)),
                *((1, y) for y in range(1, 7)),
                *((5, y) for y in range(1, 7)),
            }
        )
    ),
}


RUNNING_DOTS = ((1, 3), (3, 3), (5, 3))


def state_token(state: AgentState, role: str) -> str:
    return f"state:{state.value}:{role}"


def action_token(action: ControlAction, role: str) -> str:
    return f"action:{action.value}:{role}"


def accent_token(name: str, selected: bool) -> str:
    return f"accent:{name}:{'selected' if selected else 'unselected'}"


def compile_visual_frame(view: SurfaceView, selector_capacity: int) -> VisualFrame:
    """Compile one hardware-independent view into protocol-level light tokens."""

    state = [[OFF for _ in range(STATE_WIDTH)] for _ in range(STATE_HEIGHT)]
    if view.selected_state is None:
        for x, y in ((2, 4), (3, 4), (4, 4)):
            state[y][x] = IDLE
    else:
        token = state_token(view.selected_state, "primary")
        for x, y in STATE_GLYPHS[view.selected_state]:
            state[y][x] = token
        if view.selected_state is AgentState.RUNNING and view.activity_motion:
            active_x, active_y = RUNNING_DOTS[view.frame % len(RUNNING_DOTS)]
            for y in (active_y, active_y + 1):
                state[y][active_x] = ACTIVITY

    selectors = [OFF] * selector_capacity
    statuses = [OFF] * selector_capacity
    for session in view.sessions:
        if not 0 <= session.slot < selector_capacity:
            continue
        selectors[session.slot] = accent_token(session.accent, session.selected)
        statuses[session.slot] = state_token(session.state, "summary")

    actions = {
        action: action_token(
            action,
            "enabled" if action in view.available_actions else "disabled",
        )
        for action in ControlAction
    }
    return VisualFrame(
        state=tuple(tuple(row) for row in state),
        selectors=tuple(selectors),
        statuses=tuple(statuses),
        actions=actions,
        overflow="system:overflow" if view.overflow_count else OFF,
    )
