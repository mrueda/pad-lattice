"""Semantic interface between the daemon and a physical control surface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, TypeAlias

from pad_lattice.events import AgentState, ControlAction


@dataclass(frozen=True)
class SessionIndicator:
    """One agent session represented by a device selector slot."""

    slot: int
    state: AgentState
    selected: bool = False


@dataclass(frozen=True)
class SurfaceView:
    """Hardware-independent state rendered by a control surface."""

    selected_state: AgentState
    frame: int = 0
    sessions: tuple[SessionIndicator, ...] = ()
    available_actions: frozenset[ControlAction] = field(default_factory=frozenset)


@dataclass(frozen=True)
class ActionPressed:
    action: ControlAction


@dataclass(frozen=True)
class SessionSelected:
    slot: int


SurfaceEvent: TypeAlias = ActionPressed | SessionSelected


class ControlSurface(Protocol):
    """Operations required by the Pad-Lattice daemon and demo."""

    profile_id: str
    input_name: str
    output_name: str
    selector_capacity: int

    def initialize(self) -> None: ...

    def render(self, view: SurfaceView) -> None: ...

    def poll_events(self) -> list[SurfaceEvent]: ...

    def close(self) -> None: ...
