"""Semantic interface between the daemon and a control surface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, TypeAlias

from pad_lattice.events import AgentState, ControlAction

RgbColor: TypeAlias = tuple[int, int, int]


@dataclass(frozen=True)
class SessionIndicator:
    """One agent session represented by a surface selector slot."""

    slot: int
    state: AgentState
    selected: bool = False
    accent: str = "cyan"
    label: str = ""


@dataclass(frozen=True)
class SurfaceView:
    """Hardware-independent state rendered by a control surface."""

    selected_state: AgentState | None
    frame: int = 0
    sessions: tuple[SessionIndicator, ...] = ()
    available_actions: frozenset[ControlAction] = field(default_factory=frozenset)
    overflow_count: int = 0
    activity_motion: bool = False


@dataclass(frozen=True)
class ShowColor:
    """Exact show RGB with a semantic fallback for palette-only devices."""

    fallback: str
    rgb: RgbColor

    def __post_init__(self) -> None:
        if not self.fallback:
            raise ValueError("show color fallback must not be empty")
        if len(self.rgb) != 3 or any(
            isinstance(channel, bool)
            or not isinstance(channel, int)
            or not 0 <= channel <= 255
            for channel in self.rgb
        ):
            raise ValueError("show RGB channels must be integers from 0 to 255")


@dataclass(frozen=True)
class ShowFrame:
    """One device-independent 8x8 performance frame and its outer rails."""

    grid: tuple[tuple[ShowColor, ...], ...]
    top: tuple[ShowColor, ...]
    right: tuple[ShowColor, ...]


ExperienceKind: TypeAlias = Literal["demo", "show"]
ExperienceStatus: TypeAlias = Literal["idle", "blocked", "starting", "playing"]


@dataclass(frozen=True)
class ExperienceView:
    """Transport-neutral lifecycle state for Demo and Show playback."""

    status: ExperienceStatus
    kind: ExperienceKind | None = None
    title: str | None = None
    cue_index: int | None = None
    caption: str | None = None
    detail: str | None = None
    elapsed_ms: int = 0
    duration_ms: int | None = None
    tempo: float = 1.0
    audio_asset: str | None = None
    audio_cue: str | None = None
    audio_slot: int | None = None
    audio_sequence: int = 0
    start_delay_ms: int = 0
    reason: str | None = None


@dataclass(frozen=True)
class ActionPressed:
    action: ControlAction


@dataclass(frozen=True)
class SessionSelected:
    slot: int


@dataclass(frozen=True)
class ExperienceRequested:
    kind: ExperienceKind


@dataclass(frozen=True)
class ExperienceStopRequested:
    pass


SurfaceEvent: TypeAlias = (
    ActionPressed | SessionSelected | ExperienceRequested | ExperienceStopRequested
)


class ControlSurface(Protocol):
    """Operations required by the Pad-Lattice daemon and demo."""

    profile_id: str
    surface_kind: str
    input_name: str
    output_name: str
    selector_capacity: int
    accent_names: tuple[str, ...]
    visual_protocol: int

    def initialize(self) -> None: ...

    def render(self, view: SurfaceView) -> None: ...

    def render_show_frame(self, frame: ShowFrame) -> None: ...

    def set_experience(self, view: ExperienceView) -> None: ...

    def poll_events(self) -> list[SurfaceEvent]: ...

    def close(self) -> None: ...
