"""Portable manifests shared by physical and virtual experiences."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path, PurePosixPath
from typing import Any

from pad_lattice.devices.base import SessionIndicator, ShowColor, ShowFrame, SurfaceView
from pad_lattice.events import AgentState, ControlAction

EXPERIENCE_SCHEMA_VERSION = 1
PERFORMANCE_ID = "a-spark-becomes-a-constellation"
DEMO_ID = "multi-agent-guided-demo"
PERFORMANCE_RESOURCE = "constellation-v1.json"
DEMO_RESOURCE = "demo-v1.json"
MAX_PERFORMANCE_CUES = 4096
MAX_PERFORMANCE_COLORS = 4096


class ExperienceManifestError(ValueError):
    """Raised when a packaged experience is malformed."""


@dataclass(frozen=True)
class PerformanceCue:
    act: str
    frame: ShowFrame
    duration: float
    caption: str | None = None


@dataclass(frozen=True)
class PerformanceManifest:
    schema_version: int
    id: str
    title: str
    acts: tuple[str, ...]
    cues: tuple[PerformanceCue, ...]
    duration: float
    audio_asset: str

    def caption_at(self, cue_index: int) -> str:
        if not 0 <= cue_index < len(self.cues):
            raise ExperienceManifestError(f"unknown performance cue: {cue_index}")
        cue = self.cues[cue_index]
        for candidate in reversed(self.cues[: cue_index + 1]):
            if candidate.act != cue.act:
                break
            if candidate.caption is not None:
                return candidate.caption
        _, separator, act_title = cue.act.partition(" - ")
        return act_title if separator else cue.act


@dataclass(frozen=True)
class DemoPrompt:
    eyebrow: str
    title: str
    detail: str


@dataclass(frozen=True)
class DemoGuideTarget:
    event_type: str
    slot: int | None = None
    action: ControlAction | None = None


@dataclass(frozen=True)
class DemoTransition:
    event_type: str
    next_stage: str
    slot: int | None = None
    action: ControlAction | None = None
    audio: str | None = None


@dataclass(frozen=True)
class DemoStage:
    id: str
    prompt: DemoPrompt
    guide_target: DemoGuideTarget | None
    view: SurfaceView
    transitions: tuple[DemoTransition, ...]
    enter_audio: str | None = None
    terminal: bool = False


@dataclass(frozen=True)
class DemoManifest:
    schema_version: int
    id: str
    title: str
    initial_stage: str
    stages: tuple[DemoStage, ...]

    def stage(self, stage_id: str) -> DemoStage:
        for stage in self.stages:
            if stage.id == stage_id:
                return stage
        raise ExperienceManifestError(f"unknown demo stage: {stage_id}")


def load_builtin_performance() -> PerformanceManifest:
    return load_performance_data(
        _load_packaged_json(PERFORMANCE_RESOURCE),
        source=PERFORMANCE_RESOURCE,
    )


def load_builtin_demo() -> DemoManifest:
    return load_demo_data(
        _load_packaged_json(DEMO_RESOURCE),
        source=DEMO_RESOURCE,
    )


def load_performance_schema() -> dict[str, Any]:
    return _load_schema("performance-manifest-v1.json")


def load_demo_schema() -> dict[str, Any]:
    return _load_schema("demo-manifest-v1.json")


def load_performance_file(path: Path) -> PerformanceManifest:
    return load_performance_data(
        json.loads(path.read_text(encoding="utf-8")),
        source=str(path),
    )


def load_demo_file(path: Path) -> DemoManifest:
    return load_demo_data(
        json.loads(path.read_text(encoding="utf-8")),
        source=str(path),
    )


def load_performance_data(data: Any, *, source: str) -> PerformanceManifest:
    root = _object(data, source)
    _exact_keys(
        root,
        {
            "schema_version",
            "kind",
            "id",
            "title",
            "dimensions",
            "duration_ms",
            "acts",
            "palette",
            "cues",
            "audio",
        },
        source,
    )
    _schema_header(root, kind="performance", source=source)
    identifier = _nonempty_string(root["id"], f"{source}.id")
    title = _nonempty_string(root["title"], f"{source}.title")
    dimensions = _object(root["dimensions"], f"{source}.dimensions")
    _exact_keys(dimensions, {"grid", "top", "right"}, f"{source}.dimensions")
    if dimensions != {"grid": [8, 8], "top": 8, "right": 8}:
        raise ExperienceManifestError(
            f"{source}.dimensions must define an 8x8 grid and two eight-light rails"
        )

    acts_raw = _array(root["acts"], f"{source}.acts")
    acts = tuple(
        _nonempty_string(value, f"{source}.acts[{index}]")
        for index, value in enumerate(acts_raw)
    )
    if not acts or len(set(acts)) != len(acts):
        raise ExperienceManifestError(f"{source}.acts must contain unique entries")

    palette_raw = _array(root["palette"], f"{source}.palette")
    if not 1 <= len(palette_raw) <= MAX_PERFORMANCE_COLORS:
        raise ExperienceManifestError(
            f"{source}.palette must contain 1 to {MAX_PERFORMANCE_COLORS} colors"
        )
    palette = tuple(
        _show_color(value, f"{source}.palette[{index}]")
        for index, value in enumerate(palette_raw)
    )

    cues_raw = _array(root["cues"], f"{source}.cues")
    if not 1 <= len(cues_raw) <= MAX_PERFORMANCE_CUES:
        raise ExperienceManifestError(
            f"{source}.cues must contain 1 to {MAX_PERFORMANCE_CUES} cues"
        )
    cues = tuple(
        _performance_cue(value, index, acts, palette, source)
        for index, value in enumerate(cues_raw)
    )
    declared_duration = _positive_integer(root["duration_ms"], f"{source}.duration_ms")
    calculated_duration = sum(round(cue.duration * 1000) for cue in cues)
    if calculated_duration != declared_duration:
        raise ExperienceManifestError(
            f"{source}.duration_ms does not equal the cue timeline"
        )

    audio = _object(root["audio"], f"{source}.audio")
    _exact_keys(audio, {"asset", "mime_type", "duration_ms"}, f"{source}.audio")
    audio_asset = _safe_relative_path(audio["asset"], f"{source}.audio.asset")
    if audio["mime_type"] != "audio/wav":
        raise ExperienceManifestError(f"{source}.audio.mime_type must be audio/wav")
    if (
        _positive_integer(audio["duration_ms"], f"{source}.audio.duration_ms")
        != declared_duration
    ):
        raise ExperienceManifestError(
            f"{source}.audio.duration_ms must match the performance duration"
        )
    return PerformanceManifest(
        schema_version=EXPERIENCE_SCHEMA_VERSION,
        id=identifier,
        title=title,
        acts=acts,
        cues=cues,
        duration=declared_duration / 1000,
        audio_asset=audio_asset,
    )


def load_demo_data(data: Any, *, source: str) -> DemoManifest:
    root = _object(data, source)
    _exact_keys(
        root,
        {"schema_version", "kind", "id", "title", "initial_stage", "stages"},
        source,
    )
    _schema_header(root, kind="demo", source=source)
    stages_raw = _array(root["stages"], f"{source}.stages")
    if not 1 <= len(stages_raw) <= 64:
        raise ExperienceManifestError(f"{source}.stages must contain 1 to 64 stages")
    stages = tuple(
        _demo_stage(value, index, source)
        for index, value in enumerate(stages_raw)
    )
    stage_ids = tuple(stage.id for stage in stages)
    if len(set(stage_ids)) != len(stage_ids):
        raise ExperienceManifestError(f"{source}.stages contains duplicate IDs")
    initial_stage = _nonempty_string(root["initial_stage"], f"{source}.initial_stage")
    if initial_stage not in stage_ids:
        raise ExperienceManifestError(f"{source}.initial_stage is unknown")
    for stage in stages:
        if stage.terminal and stage.transitions:
            raise ExperienceManifestError(
                f"{source}.stages[{stage.id}] is terminal but has transitions"
            )
        if not stage.terminal and not stage.transitions:
            raise ExperienceManifestError(
                f"{source}.stages[{stage.id}] is nonterminal but has no transitions"
            )
        if stage.terminal and stage.guide_target is not None:
            raise ExperienceManifestError(
                f"{source}.stages[{stage.id}] is terminal but has a guide target"
            )
        if not stage.terminal and stage.guide_target is None:
            raise ExperienceManifestError(
                f"{source}.stages[{stage.id}] has no guide target"
            )
        visible_slots = {session.slot for session in stage.view.sessions}
        for transition in stage.transitions:
            if transition.next_stage not in stage_ids:
                raise ExperienceManifestError(
                    f"{source}.stages[{stage.id}] targets an unknown stage"
                )
            if (
                transition.event_type == "select"
                and transition.slot not in visible_slots
            ):
                raise ExperienceManifestError(
                    f"{source}.stages[{stage.id}] selects a missing session"
                )
            if (
                transition.event_type == "action"
                and transition.action not in stage.view.available_actions
            ):
                raise ExperienceManifestError(
                    f"{source}.stages[{stage.id}] uses an unavailable action"
                )
        if stage.guide_target is not None and not any(
            transition.event_type == stage.guide_target.event_type
            and transition.slot == stage.guide_target.slot
            and transition.action == stage.guide_target.action
            for transition in stage.transitions
        ):
            raise ExperienceManifestError(
                f"{source}.stages[{stage.id}] guide target is not a transition"
            )
    reachable = {initial_stage}
    while True:
        discovered = {
            transition.next_stage
            for stage in stages
            if stage.id in reachable
            for transition in stage.transitions
        }
        expanded = reachable | discovered
        if expanded == reachable:
            break
        reachable = expanded
    if reachable != set(stage_ids):
        raise ExperienceManifestError(f"{source}.stages contains unreachable stages")
    return DemoManifest(
        schema_version=EXPERIENCE_SCHEMA_VERSION,
        id=_nonempty_string(root["id"], f"{source}.id"),
        title=_nonempty_string(root["title"], f"{source}.title"),
        initial_stage=initial_stage,
        stages=stages,
    )


def _performance_cue(
    value: Any,
    index: int,
    acts: tuple[str, ...],
    palette: tuple[ShowColor, ...],
    source: str,
) -> PerformanceCue:
    context = f"{source}.cues[{index}]"
    cue = _object(value, context)
    _exact_keys(cue, {"act", "duration_ms", "caption", "frame"}, context)
    act_index = _integer(cue["act"], f"{context}.act")
    if not 0 <= act_index < len(acts):
        raise ExperienceManifestError(f"{context}.act is outside the acts array")
    caption = cue["caption"]
    if caption is not None:
        caption = _nonempty_string(caption, f"{context}.caption")
    frame_data = _object(cue["frame"], f"{context}.frame")
    _exact_keys(frame_data, {"grid", "top", "right"}, f"{context}.frame")
    grid_raw = _array(frame_data["grid"], f"{context}.frame.grid")
    if len(grid_raw) != 8:
        raise ExperienceManifestError(f"{context}.frame.grid must have eight rows")
    grid = tuple(
        tuple(
            palette[
                _palette_index(
                    item,
                    len(palette),
                    f"{context}.frame.grid[{row}][{column}]",
                )
            ]
            for column, item in enumerate(
                _eight_items(values, f"{context}.frame.grid[{row}]")
            )
        )
        for row, values in enumerate(grid_raw)
    )
    top = tuple(
        palette[
            _palette_index(
                item,
                len(palette),
                f"{context}.frame.top[{column}]",
            )
        ]
        for column, item in enumerate(
            _eight_items(frame_data["top"], f"{context}.frame.top")
        )
    )
    right = tuple(
        palette[
            _palette_index(
                item,
                len(palette),
                f"{context}.frame.right[{row}]",
            )
        ]
        for row, item in enumerate(
            _eight_items(frame_data["right"], f"{context}.frame.right")
        )
    )
    return PerformanceCue(
        act=acts[act_index],
        frame=ShowFrame(grid=grid, top=top, right=right),
        duration=_positive_integer(cue["duration_ms"], f"{context}.duration_ms") / 1000,
        caption=caption,
    )


def _demo_stage(value: Any, index: int, source: str) -> DemoStage:
    context = f"{source}.stages[{index}]"
    stage = _object(value, context)
    _exact_keys(
        stage,
        {
            "id",
            "prompt",
            "guide_target",
            "view",
            "transitions",
            "enter_audio",
            "terminal",
        },
        context,
    )
    prompt_data = _object(stage["prompt"], f"{context}.prompt")
    _exact_keys(prompt_data, {"eyebrow", "title", "detail"}, f"{context}.prompt")
    prompt = DemoPrompt(
        eyebrow=_nonempty_string(
            prompt_data["eyebrow"],
            f"{context}.prompt.eyebrow",
        ),
        title=_nonempty_string(prompt_data["title"], f"{context}.prompt.title"),
        detail=_nonempty_string(prompt_data["detail"], f"{context}.prompt.detail"),
    )
    guide_target = _demo_guide_target(stage["guide_target"], context)
    view_data = _object(stage["view"], f"{context}.view")
    _exact_keys(view_data, {"sessions", "available_actions"}, f"{context}.view")
    sessions = tuple(
        _demo_session(item, slot, f"{context}.view.sessions[{slot}]")
        for slot, item in enumerate(_array(view_data["sessions"], f"{context}.view.sessions"))
    )
    if len(sessions) > 8 or len({session.slot for session in sessions}) != len(sessions):
        raise ExperienceManifestError(f"{context}.view.sessions must use unique slots 0 to 7")
    selected = [session for session in sessions if session.selected]
    if len(selected) > 1:
        raise ExperienceManifestError(f"{context}.view selects more than one session")
    actions = frozenset(
        _control_action(item, f"{context}.view.available_actions[{item_index}]")
        for item_index, item in enumerate(
            _array(
                view_data["available_actions"],
                f"{context}.view.available_actions",
            )
        )
    )
    transitions = tuple(
        _demo_transition(item, transition_index, context)
        for transition_index, item in enumerate(
            _array(stage["transitions"], f"{context}.transitions")
        )
    )
    enter_audio = stage["enter_audio"]
    if enter_audio is not None:
        enter_audio = _nonempty_string(enter_audio, f"{context}.enter_audio")
    if not isinstance(stage["terminal"], bool):
        raise ExperienceManifestError(f"{context}.terminal must be boolean")
    return DemoStage(
        id=_nonempty_string(stage["id"], f"{context}.id"),
        prompt=prompt,
        guide_target=guide_target,
        view=SurfaceView(
            selected_state=selected[0].state if selected else None,
            sessions=sessions,
            available_actions=actions,
        ),
        transitions=transitions,
        enter_audio=enter_audio,
        terminal=stage["terminal"],
    )


def _demo_guide_target(value: Any, context: str) -> DemoGuideTarget | None:
    if value is None:
        return None
    target_context = f"{context}.guide_target"
    target = _object(value, target_context)
    _exact_keys(target, {"event", "slot", "action"}, target_context)
    event_type = target["event"]
    if event_type == "select":
        slot = _integer(target["slot"], f"{target_context}.slot")
        if not 0 <= slot < 8 or target["action"] is not None:
            raise ExperienceManifestError(f"{target_context} has invalid select input")
        return DemoGuideTarget(event_type="select", slot=slot)
    if event_type == "action":
        if target["slot"] is not None:
            raise ExperienceManifestError(f"{target_context} has invalid action input")
        return DemoGuideTarget(
            event_type="action",
            action=_control_action(target["action"], f"{target_context}.action"),
        )
    raise ExperienceManifestError(f"{target_context}.event is unknown")


def _demo_session(value: Any, fallback_slot: int, context: str) -> SessionIndicator:
    session = _object(value, context)
    _exact_keys(session, {"slot", "state", "selected", "accent", "label"}, context)
    slot = _integer(session["slot"], f"{context}.slot")
    if not 0 <= slot < 8:
        raise ExperienceManifestError(f"{context}.slot must be from 0 to 7")
    if slot != fallback_slot:
        raise ExperienceManifestError(f"{context}.slot must match its array position")
    try:
        state = AgentState(session["state"])
    except (TypeError, ValueError) as exc:
        raise ExperienceManifestError(f"{context}.state is unknown") from exc
    if not isinstance(session["selected"], bool):
        raise ExperienceManifestError(f"{context}.selected must be boolean")
    return SessionIndicator(
        slot=slot,
        state=state,
        selected=session["selected"],
        accent=_nonempty_string(session["accent"], f"{context}.accent"),
        label=_nonempty_string(session["label"], f"{context}.label"),
    )


def _demo_transition(value: Any, index: int, context: str) -> DemoTransition:
    transition_context = f"{context}.transitions[{index}]"
    transition = _object(value, transition_context)
    _exact_keys(
        transition,
        {"event", "slot", "action", "next_stage", "audio"},
        transition_context,
    )
    event_type = transition["event"]
    if event_type not in {"select", "action"}:
        raise ExperienceManifestError(f"{transition_context}.event is unknown")
    slot = transition["slot"]
    action = transition["action"]
    if event_type == "select":
        slot = _integer(slot, f"{transition_context}.slot")
        if not 0 <= slot < 8 or action is not None:
            raise ExperienceManifestError(
                f"{transition_context} has invalid select input"
            )
        parsed_action = None
    else:
        if slot is not None:
            raise ExperienceManifestError(
                f"{transition_context} has invalid action input"
            )
        parsed_action = _control_action(action, f"{transition_context}.action")
    audio = transition["audio"]
    if audio is not None:
        audio = _nonempty_string(audio, f"{transition_context}.audio")
    return DemoTransition(
        event_type=event_type,
        slot=slot,
        action=parsed_action,
        next_stage=_nonempty_string(
            transition["next_stage"],
            f"{transition_context}.next_stage",
        ),
        audio=audio,
    )


def _load_packaged_json(name: str) -> Any:
    resource = resources.files("pad_lattice").joinpath(
        "web_dist", "play", "experiences", name
    )
    try:
        return json.loads(resource.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ExperienceManifestError(f"packaged experience is missing: {name}") from exc


def _load_schema(name: str) -> dict[str, Any]:
    schema = resources.files("pad_lattice").joinpath("schemas", name)
    return json.loads(schema.read_text(encoding="utf-8"))


def _schema_header(root: dict[str, Any], *, kind: str, source: str) -> None:
    version = _integer(root["schema_version"], f"{source}.schema_version")
    if version != EXPERIENCE_SCHEMA_VERSION:
        raise ExperienceManifestError(
            f"{source}: unsupported schema_version {version}; expected {EXPERIENCE_SCHEMA_VERSION}"
        )
    if root["kind"] != kind:
        raise ExperienceManifestError(f"{source}.kind must be {kind!r}")


def _show_color(value: Any, context: str) -> ShowColor:
    item = _object(value, context)
    _exact_keys(item, {"fallback", "rgb"}, context)
    rgb_raw = _array(item["rgb"], f"{context}.rgb")
    if len(rgb_raw) != 3:
        raise ExperienceManifestError(f"{context}.rgb must contain three channels")
    channels = tuple(
        _integer(channel, f"{context}.rgb[{index}]")
        for index, channel in enumerate(rgb_raw)
    )
    rgb = (channels[0], channels[1], channels[2])
    try:
        return ShowColor(
            fallback=_nonempty_string(item["fallback"], f"{context}.fallback"),
            rgb=rgb,
        )
    except ValueError as exc:
        raise ExperienceManifestError(f"{context}: {exc}") from exc


def _palette_index(value: Any, palette_size: int, context: str) -> int:
    index = _integer(value, context)
    if not 0 <= index < palette_size:
        raise ExperienceManifestError(f"{context} is outside the palette")
    return index


def _eight_items(value: Any, context: str) -> list[Any]:
    items = _array(value, context)
    if len(items) != 8:
        raise ExperienceManifestError(f"{context} must contain eight items")
    return items


def _safe_relative_path(value: Any, context: str) -> str:
    path = PurePosixPath(_nonempty_string(value, context))
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ExperienceManifestError(f"{context} must be a safe relative path")
    return str(path)


def _control_action(value: Any, context: str) -> ControlAction:
    try:
        return ControlAction(value)
    except (TypeError, ValueError) as exc:
        raise ExperienceManifestError(f"{context} is an unknown action") from exc


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ExperienceManifestError(f"{context} must be an object")
    return value


def _array(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ExperienceManifestError(f"{context} must be an array")
    return value


def _integer(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ExperienceManifestError(f"{context} must be an integer")
    return value


def _positive_integer(value: Any, context: str) -> int:
    parsed = _integer(value, context)
    if parsed <= 0:
        raise ExperienceManifestError(f"{context} must be positive")
    return parsed


def _nonempty_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExperienceManifestError(f"{context} must be a non-empty string")
    return value


def _exact_keys(value: dict[str, Any], expected: set[str], context: str) -> None:
    missing = expected - set(value)
    extra = set(value) - expected
    if missing:
        raise ExperienceManifestError(f"{context} is missing {sorted(missing)[0]!r}")
    if extra:
        raise ExperienceManifestError(f"{context} contains unknown {sorted(extra)[0]!r}")
