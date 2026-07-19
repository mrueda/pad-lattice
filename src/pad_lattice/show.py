"""Authored full-surface visual performances."""

from __future__ import annotations

import colorsys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TextIO

from pad_lattice.audio import StoryBeat
from pad_lattice.devices.base import ControlSurface, ShowColor, ShowFrame
from pad_lattice.experience_manifest import load_builtin_performance

SHOW_TITLE = "A Spark Becomes a Constellation"
SHOW_WIDTH = 8
SHOW_HEIGHT = 8
SHOW_ACTS = (
    "Prelude - Alone",
    "Act I - An Idea",
    "Act II - The Search",
    "Act III - A Friend",
    "Act IV - The Storm",
    "Act V - The Call",
    "Act VI - Together",
    "Finale - A Constellation",
)

OFF = "off"
WHITE = "state:waiting_for_reply:primary"
WHITE_DIM = "state:waiting_for_reply:summary"
BLUE = "state:running:primary"
BLUE_DIM = "state:running:summary"
GREEN = "state:success:primary"
GREEN_DIM = "state:success:summary"
RED = "state:error:primary"
RED_DIM = "state:error:summary"
AMBER = "state:waiting_for_approval:primary"
AMBER_DIM = "state:waiting_for_approval:summary"

ACCENTS = ("cyan", "magenta", "lime", "orange", "violet", "teal", "rose", "sky")
BRIGHT = tuple(f"accent:{name}:selected" for name in ACCENTS)
DIM = tuple(f"accent:{name}:unselected" for name in ACCENTS)
DIM_TOKEN = dict(zip(BRIGHT, DIM))
SHOW_TOKENS = frozenset(
    {
        OFF,
        WHITE,
        WHITE_DIM,
        BLUE,
        BLUE_DIM,
        GREEN,
        GREEN_DIM,
        RED,
        RED_DIM,
        AMBER,
        AMBER_DIM,
        *BRIGHT,
        *DIM,
    }
)
SHOW_RGB: Mapping[str, tuple[int, int, int]] = {
    OFF: (0, 0, 0),
    WHITE: (238, 248, 255),
    WHITE_DIM: (18, 28, 42),
    BLUE: (42, 92, 255),
    BLUE_DIM: (8, 18, 58),
    GREEN: (28, 235, 132),
    GREEN_DIM: (5, 48, 31),
    RED: (255, 38, 32),
    RED_DIM: (65, 5, 12),
    AMBER: (255, 158, 24),
    AMBER_DIM: (68, 25, 3),
    **dict(
        zip(
            BRIGHT,
            (
                (0, 222, 255),
                (255, 35, 178),
                (164, 255, 38),
                (255, 92, 18),
                (145, 66, 255),
                (0, 196, 148),
                (255, 66, 102),
                (62, 158, 255),
            ),
        )
    ),
    **dict(
        zip(
            DIM,
            (
                (0, 43, 55),
                (58, 4, 39),
                (34, 55, 6),
                (62, 18, 2),
                (28, 11, 61),
                (0, 45, 34),
                (61, 8, 20),
                (9, 31, 64),
            ),
        )
    ),
}

Point = tuple[int, int]
ColorSpec = str | ShowColor
Pixels = Mapping[Point, ColorSpec]


@dataclass(frozen=True)
class ShowCue:
    """One held frame in an authored visual story."""

    act: str
    frame: ShowFrame
    duration: float
    caption: str | None = None


def build_constellation_show() -> tuple[ShowCue, ...]:
    """Load the compiled reference performance used by every runtime."""

    performance = load_builtin_performance()
    return tuple(
        ShowCue(
            act=cue.act,
            frame=cue.frame,
            duration=cue.duration,
            caption=cue.caption,
        )
        for cue in performance.cues
    )


def _author_constellation_show() -> tuple[ShowCue, ...]:
    """Build the source performance consumed only by the asset compiler."""

    cues: list[ShowCue] = []
    _add_alone(cues)
    _add_idea(cues)
    _add_search(cues)
    _add_friend(cues)
    _add_storm(cues)
    _add_call(cues)
    _add_together(cues)
    _add_finale(cues)
    return tuple(cues)


def run_show_surface(
    surface: ControlSurface,
    *,
    tempo: float = 1.0,
    audio: bool = False,
    wait_for_request: bool = False,
    output: TextIO | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    """Play the compiled performance using the shared absolute-time engine."""

    from pad_lattice.experience_runtime import run_experience_loop

    controller = run_experience_loop(
        surface,
        "show",
        tempo=tempo,
        host_show_audio=audio,
        wait_for_request=wait_for_request,
        output=output,
        clock=clock,
        sleep=sleep,
    )
    return controller.last_reason == "complete"


def show_duration(cues: Sequence[ShowCue], *, tempo: float = 1.0) -> float:
    if tempo <= 0:
        raise ValueError("show tempo must be positive")
    return sum(cue.duration for cue in cues) / tempo


def _story_timeline(
    cues: Sequence[ShowCue],
    *,
    tempo: float,
) -> tuple[StoryBeat, ...]:
    elapsed = 0.0
    timeline: list[StoryBeat] = []
    for cue in cues:
        duration = cue.duration / tempo
        timeline.append(StoryBeat(cue.act, cue.caption, elapsed, duration))
        elapsed += duration
    return tuple(timeline)


def _add_alone(cues: list[ShowCue]) -> None:
    act = SHOW_ACTS[0]
    top, right = _chapter_rails(0, WHITE_DIM)
    _cue(cues, act, {}, 0.8, caption="Alone")
    _cue(cues, act, {(3, 4): DIM[0]}, 0.65, top=top, right=right)
    top, right = _chapter_rails(0, BRIGHT[0])
    _cue(cues, act, {(3, 4): BRIGHT[0]}, 0.85, top=top, right=right)


def _add_idea(cues: list[ShowCue]) -> None:
    act = SHOW_ACTS[1]
    top, right = _chapter_rails(1, AMBER)
    center = (3, 4)
    small_spark = {
        center: WHITE,
        (3, 3): AMBER_DIM,
        (2, 4): AMBER_DIM,
        (4, 4): AMBER_DIM,
        (3, 5): AMBER_DIM,
    }
    large_spark = {
        **small_spark,
        (2, 3): AMBER,
        (4, 3): AMBER,
        (2, 5): AMBER,
        (4, 5): AMBER,
    }
    _cue(cues, act, small_spark, 0.45, top=top, right=right)
    _cue(cues, act, large_spark, 0.45, top=top, right=right)
    bulb = _light_bulb_pixels()
    _cue(cues, act, _dimmed(bulb), 0.55, top=top, right=right)
    _cue(
        cues,
        act,
        bulb,
        1.25,
        top=top,
        right=right,
        caption="An idea",
    )


def _add_search(cues: list[ShowCue]) -> None:
    act = SHOW_ACTS[2]
    top, right = _chapter_rails(2, BRIGHT[0])
    bulb = _light_bulb_pixels()
    question = _question_pixels()
    magnifier = _magnifier_pixels()
    _cue(cues, act, _dimmed(bulb), 0.45, top=top, right=right)
    _cue(
        cues,
        act,
        question,
        1.25,
        top=top,
        right=right,
        caption="A question",
    )
    _cue(cues, act, _dimmed(question), 0.35, top=top, right=right)
    _cue(
        cues,
        act,
        magnifier,
        1.2,
        top=top,
        right=right,
        caption="The search",
    )
    target_path = ((2, 2), (3, 2), (4, 3), (3, 3))
    for index, point in enumerate(target_path):
        pixels = dict(magnifier)
        if index:
            pixels[target_path[index - 1]] = WHITE_DIM
        pixels[point] = WHITE
        scan_top = list(top)
        scan_right = list(right)
        scan_top[point[0]] = WHITE
        scan_right[point[1]] = WHITE
        _cue(cues, act, pixels, 0.32, top=scan_top, right=scan_right)
    _cue(cues, act, _dimmed(magnifier), 0.4, top=top, right=right)


def _add_friend(cues: list[ShowCue]) -> None:
    act = SHOW_ACTS[3]
    top, right = _chapter_rails(3, BRIGHT[1])
    cyan_path = ((0, 3), (1, 3), (2, 3))
    magenta_path = ((7, 4), (6, 4), (5, 4))
    for index, (cyan, magenta) in enumerate(zip(cyan_path, magenta_path)):
        pixels: dict[Point, str] = {}
        if index:
            pixels[cyan_path[index - 1]] = DIM[0]
            pixels[magenta_path[index - 1]] = DIM[1]
        pixels[cyan] = BRIGHT[0]
        pixels[magenta] = BRIGHT[1]
        _cue(cues, act, pixels, 0.42, top=top, right=right)

    people = _people_pixels()
    _cue(
        cues,
        act,
        people,
        1.3,
        top=top,
        right=right,
        caption="A friend",
    )
    _cue(
        cues,
        act,
        _people_pixels(connected=True),
        0.8,
        top=top,
        right=right,
        caption="A connection",
    )
    _cue(
        cues,
        act,
        _heart_pixels(),
        1.4,
        top=top,
        right=right,
        caption="Hope",
    )


def _add_storm(cues: list[ShowCue]) -> None:
    act = SHOW_ACTS[4]
    top, right = _chapter_rails(4, RED)
    dim_heart = _dimmed(_heart_pixels())
    _cue(cues, act, dim_heart, 0.45, top=top, right=right)
    bolt = _lightning_points()
    for end in (3, 5, 7, len(bolt)):
        pixels = dict(dim_heart)
        for index, point in enumerate(bolt[:end]):
            pixels[point] = AMBER if index == end - 1 else RED
        _cue(cues, act, pixels, 0.25, top=top, right=right)
    storm = dict(dim_heart)
    storm.update({point: RED for point in bolt})
    _cue(
        cues,
        act,
        storm,
        0.65,
        top=(RED,) * 8,
        right=(RED_DIM,) * 8,
        caption="The storm",
    )
    _cue(
        cues,
        act,
        _broken_heart_pixels(),
        1.2,
        top=top,
        right=right,
        caption="Loss",
    )
    _cue(
        cues,
        act,
        _face_pixels(happy=False, token=BLUE_DIM),
        1.3,
        top=top,
        right=right,
    )
    _cue(cues, act, {(3, 4): DIM[0]}, 0.6, top=top, right=right)


def _add_call(cues: list[ShowCue]) -> None:
    act = SHOW_ACTS[5]
    top, right = _chapter_rails(5, BRIGHT[4])
    _cue(cues, act, {(3, 4): BRIGHT[0]}, 0.6, top=top, right=right)
    resolve = _exclamation_pixels()
    _cue(cues, act, _dimmed(resolve), 0.45, top=top, right=right)
    _cue(
        cues,
        act,
        resolve,
        1.0,
        top=top,
        right=right,
        caption="Courage",
    )

    center = (3, 4)
    for radius, token in enumerate((BRIGHT[0], BLUE, BRIGHT[4], WHITE), start=1):
        pixels = {center: WHITE}
        if radius > 1:
            pixels.update(
                {point: DIM[0] for point in _ring(center, radius - 1)}
            )
        pixels.update({point: token for point in _ring(center, radius)})
        _cue(
            cues,
            act,
            pixels,
            0.35,
            top=top,
            right=right,
            caption="A call" if radius == 1 else None,
        )

    nodes = ((0, 0), (3, 0), (7, 0), (7, 3), (7, 7), (4, 7), (0, 7), (0, 4))
    targets = ((3, 3), (3, 3), (4, 3), (4, 3), (4, 4), (4, 4), (3, 4), (3, 4))
    signal_edge = {point: DIM[0] for point in _ring(center, 4)}
    signal_edge[nodes[0]] = BRIGHT[0]
    _cue(
        cues,
        act,
        signal_edge,
        0.25,
        top=(BRIGHT[0],) + (OFF,) * 7,
        right=(OFF,) * 7 + (BRIGHT[0],),
    )
    fading_signal = {
        point: DIM[0]
        for point in _ring(center, 4)
        if (point[0] + point[1]) % 2 == 0
    }
    fading_signal[nodes[0]] = BRIGHT[0]
    _cue(
        cues,
        act,
        fading_signal,
        0.25,
        top=(BRIGHT[0],) + (OFF,) * 7,
        right=(OFF,) * 7 + (BRIGHT[0],),
        caption="An answer",
    )
    gathered: dict[Point, str] = {}
    for index, node in enumerate(nodes):
        gathered[node] = BRIGHT[index]
        rail_top = tuple(BRIGHT[i] if i <= index else OFF for i in range(8))
        rail_right = tuple(reversed(rail_top))
        _cue(
            cues,
            act,
            gathered,
            0.25,
            top=rail_top,
            right=rail_right,
        )

    for count in range(1, len(nodes) + 1):
        pixels = {node: BRIGHT[index] for index, node in enumerate(nodes)}
        for index in range(count):
            token = BRIGHT[index]
            for point in _line(nodes[index], targets[index]):
                pixels[point] = token
        for center in ((3, 3), (4, 3), (3, 4), (4, 4)):
            pixels[center] = WHITE
        top = tuple(BRIGHT[index] if index < count else OFF for index in range(8))
        right = tuple(BRIGHT[7 - index] if index < count else OFF for index in range(8))
        _cue(cues, act, pixels, 0.28, top=top, right=right)
    _cue(
        cues,
        act,
        _lattice_pixels(),
        1.1,
        top=tuple(BRIGHT),
        right=tuple(reversed(BRIGHT)),
        caption="A community",
    )


def _add_together(cues: list[ShowCue]) -> None:
    act = SHOW_ACTS[6]
    top, right = _chapter_rails(6, GREEN)
    lattice = _lattice_pixels()
    _cue(cues, act, _dimmed(lattice), 0.45, top=top, right=right)
    check = _check_pixels()
    _cue(cues, act, _dimmed(check), 0.45, top=top, right=right)
    _cue(
        cues,
        act,
        check,
        1.2,
        top=top,
        right=right,
        caption="Together, a solution",
    )
    _cue(
        cues,
        act,
        _face_pixels(happy=True, token=GREEN),
        1.3,
        top=top,
        right=right,
        caption="Joy",
    )
    heart = _heart_pixels(spectrum=True)
    _cue(cues, act, heart, 1.2, top=tuple(BRIGHT), right=tuple(reversed(BRIGHT)))


def _add_finale(cues: list[ShowCue]) -> None:
    act = SHOW_ACTS[7]
    for count in (16, 32, 64):
        _cue(
            cues,
            act,
            _constellation_pixels(0, count=count),
            0.3,
            top=tuple(BRIGHT),
            right=tuple(reversed(BRIGHT)),
            caption="A constellation" if count == 64 else None,
        )

    for phase in range(6):
        _cue(
            cues,
            act,
            _constellation_pixels(phase, count=64),
            0.22,
            top=_rotating_rail(phase),
            right=_rotating_rail(-phase),
        )

    heart = _heart_pixels(spectrum=True)
    _cue(cues, act, heart, 1.0, top=tuple(BRIGHT), right=tuple(reversed(BRIGHT)))

    logo = _logo_pixels()
    for rows in (2, 4, 6, 8):
        partial = {
            point: token
            for point, token in logo.items()
            if point[1] < rows
        }
        partial.update(
            {
                point: DIM[(point[0] + point[1]) % len(DIM)]
                for point in heart
                if point[1] >= rows and point not in partial
            }
        )
        _cue(
            cues,
            act,
            partial,
            0.4,
            top=_rotating_rail(rows),
            right=_rotating_rail(-rows),
        )
    _cue(
        cues,
        act,
        logo,
        2.2,
        top=tuple(BRIGHT),
        right=tuple(reversed(BRIGHT)),
        caption="Pad-Lattice",
    )
    _cue(cues, act, _dimmed(logo), 0.7, top=tuple(DIM), right=tuple(reversed(DIM)))
    _cue(cues, act, {(3, 4): BRIGHT[0]}, 0.8, caption="No light alone")
    _cue(cues, act, {}, 0.8)


def _cue(
    cues: list[ShowCue],
    act: str,
    pixels: Pixels,
    duration: float,
    *,
    top: Sequence[str] | None = None,
    right: Sequence[str] | None = None,
    caption: str | None = None,
) -> None:
    cues.append(
        ShowCue(
            act=act,
            frame=_frame(pixels, top=top, right=right),
            duration=duration,
            caption=caption,
        )
    )


def _frame(
    pixels: Pixels,
    *,
    top: Sequence[str] | None = None,
    right: Sequence[str] | None = None,
) -> ShowFrame:
    grid: list[list[ColorSpec]] = [
        [OFF for _ in range(SHOW_WIDTH)] for _ in range(SHOW_HEIGHT)
    ]
    for (x, y), color in pixels.items():
        if not 0 <= x < SHOW_WIDTH or not 0 <= y < SHOW_HEIGHT:
            raise ValueError(f"show pixel is outside the 8x8 grid: {(x, y)}")
        _validate_show_color(color)
        grid[y][x] = color
    top_tokens = tuple(top) if top is not None else (OFF,) * SHOW_WIDTH
    right_tokens = tuple(right) if right is not None else (OFF,) * SHOW_HEIGHT
    if len(top_tokens) != SHOW_WIDTH or len(right_tokens) != SHOW_HEIGHT:
        raise ValueError("show rails must each contain eight lights")
    for color in (*top_tokens, *right_tokens):
        _validate_show_color(color)
    return ShowFrame(
        grid=tuple(tuple(_show_color(color) for color in row) for row in grid),
        top=tuple(_show_color(color) for color in top_tokens),
        right=tuple(_show_color(color) for color in right_tokens),
    )


def _validate_show_color(color: ColorSpec) -> None:
    fallback = color.fallback if isinstance(color, ShowColor) else color
    if fallback not in SHOW_TOKENS:
        raise ValueError(f"unknown show color token: {fallback}")


def _show_color(color: ColorSpec) -> ShowColor:
    if isinstance(color, ShowColor):
        return color
    return ShowColor(color, SHOW_RGB[color])


def _hsv_color(
    fallback: str,
    hue: float,
    saturation: float,
    value: float,
) -> ShowColor:
    red, green, blue = colorsys.hsv_to_rgb(
        hue % 1.0,
        max(0.0, min(1.0, saturation)),
        max(0.0, min(1.0, value)),
    )
    return ShowColor(
        fallback,
        tuple(round(channel * 255) for channel in (red, green, blue)),
    )


def _chapter_rails(chapter: int, token: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    top = [OFF] * 8
    for index in range(chapter):
        top[index] = DIM[index]
    top[chapter] = token
    return tuple(top), tuple(reversed(top))


def _ring(center: Point, radius: int) -> tuple[Point, ...]:
    cx, cy = center
    return tuple(
        (x, y)
        for y in range(SHOW_HEIGHT)
        for x in range(SHOW_WIDTH)
        if max(abs(x - cx), abs(y - cy)) == radius
    )


def _rotating_rail(phase: int) -> tuple[str, ...]:
    return tuple(BRIGHT[(index + phase) % len(BRIGHT)] for index in range(8))


def _pattern_pixels(
    pattern: Sequence[str],
    palette: Mapping[str, str],
) -> dict[Point, str]:
    if len(pattern) != SHOW_HEIGHT or any(len(row) != SHOW_WIDTH for row in pattern):
        raise ValueError("show icon patterns must be 8x8")
    pixels: dict[Point, str] = {}
    for y, row in enumerate(pattern):
        for x, marker in enumerate(row):
            if marker == ".":
                continue
            try:
                pixels[(x, y)] = palette[marker]
            except KeyError as exc:
                raise ValueError(f"show icon uses unknown marker: {marker}") from exc
    return pixels


def _light_bulb_pixels() -> dict[Point, str]:
    return _pattern_pixels(
        (
            "..AAAA..",
            ".A....A.",
            "A..WW..A",
            "A..WW..A",
            ".A....A.",
            "..AAAA..",
            "...AA...",
            "..AAAA..",
        ),
        {"A": AMBER, "W": WHITE},
    )


def _question_pixels() -> dict[Point, str]:
    return _pattern_pixels(
        (
            "..CCCC..",
            ".CC..CC.",
            ".....CC.",
            "....CC..",
            "...CC...",
            "...CC...",
            "........",
            "...CC...",
        ),
        {"C": BRIGHT[0]},
    )


def _magnifier_pixels() -> dict[Point, str]:
    return _pattern_pixels(
        (
            ".CCCC...",
            "C....C..",
            "C....C..",
            "C....C..",
            ".CCCC...",
            "....CC..",
            ".....CC.",
            "......C.",
        ),
        {"C": BRIGHT[0]},
    )


def _people_pixels(*, connected: bool = False) -> dict[Point, str]:
    bridge = "CCCWWMMM" if connected else "CCC..MMM"
    return _pattern_pixels(
        (
            "........",
            ".C....M.",
            ".C....M.",
            bridge,
            ".C....M.",
            "C.C..M.M",
            "C.C..M.M",
            "........",
        ),
        {"C": BRIGHT[0], "M": BRIGHT[1], "W": WHITE},
    )


def _lightning_points() -> tuple[Point, ...]:
    return ((6, 0), (5, 1), (4, 2), (3, 3), (4, 3), (3, 4), (2, 5), (1, 6), (0, 7))


def _broken_heart_pixels() -> dict[Point, str]:
    pixels = _dimmed(_heart_pixels())
    crack = ((3, 1), (4, 1), (3, 2), (4, 3), (3, 4), (4, 5), (3, 6))
    for point in crack:
        pixels.pop(point, None)
    return pixels


def _face_pixels(*, happy: bool, token: str) -> dict[Point, str]:
    mouth = (
        ((1, 4), (2, 5), (3, 6), (4, 6), (5, 5), (6, 4))
        if happy
        else ((1, 6), (2, 5), (3, 4), (4, 4), (5, 5), (6, 6))
    )
    pixels = {point: token for point in mouth}
    pixels[(2, 2)] = WHITE
    pixels[(5, 2)] = WHITE
    return pixels


def _exclamation_pixels() -> dict[Point, str]:
    return _pattern_pixels(
        (
            "...CC...",
            "...CC...",
            "...CC...",
            "...CC...",
            "...CC...",
            "........",
            "...CC...",
            "...CC...",
        ),
        {"C": BRIGHT[0]},
    )


def _check_pixels() -> dict[Point, str]:
    return _pattern_pixels(
        (
            "........",
            "......GG",
            ".....GG.",
            "....GG..",
            "G..GG...",
            "GGGG....",
            ".GG.....",
            "........",
        ),
        {"G": GREEN},
    )


def _constellation_pixels(phase: int, *, count: int) -> dict[Point, ColorSpec]:
    if not 0 <= count <= SHOW_WIDTH * SHOW_HEIGHT:
        raise ValueError("constellation light count must be between 0 and 64")
    points = sorted(
        ((x, y) for y in range(SHOW_HEIGHT) for x in range(SHOW_WIDTH)),
        key=lambda point: (
            max(abs(point[0] - 3.5), abs(point[1] - 3.5)),
            (point[0] * 3 + point[1] * 5) % 8,
        ),
    )
    pixels: dict[Point, ColorSpec] = {}
    for x, y in points[:count]:
        color = (x + y + phase) % len(BRIGHT)
        bright = (x - y + phase) % 4 == 0
        fallback = BRIGHT[color] if bright else DIM[color]
        hue = ((x * 47 + y * 29 + phase * 23) % 360) / 360
        saturation = 0.68 + 0.2 * ((x + y) % 3) / 2
        value = 0.96 if bright else 0.3 + 0.08 * ((x * 3 + y) % 3)
        pixels[(x, y)] = _hsv_color(fallback, hue, saturation, value)
    return pixels


def _heart_pixels(*, spectrum: bool = False) -> dict[Point, ColorSpec]:
    pattern = (
        ".XX..XX.",
        "XXXXXXXX",
        "XXXXXXXX",
        "XXXXXXXX",
        ".XXXXXX.",
        "..XXXX..",
        "...XX...",
        "........",
    )
    pixels: dict[Point, ColorSpec] = {}
    for y, row in enumerate(pattern):
        for x, value in enumerate(row):
            if value == "X":
                if spectrum:
                    color_index = (x + y) % len(BRIGHT)
                    hue = ((x * 41 + y * 17) % 360) / 360
                    fallback = BRIGHT[color_index]
                else:
                    hue = 0.52 + 0.4 * x / (SHOW_WIDTH - 1)
                    fallback = BRIGHT[0] if x < 4 else BRIGHT[1]
                brightness = 0.72 + 0.24 * (SHOW_HEIGHT - 1 - y) / (SHOW_HEIGHT - 1)
                pixels[(x, y)] = _hsv_color(
                    fallback,
                    hue,
                    0.78,
                    brightness,
                )
    warm_white = ShowColor(WHITE, (255, 226, 180))
    pixels[(3, 3)] = warm_white
    pixels[(4, 3)] = warm_white
    return pixels


def _lattice_pixels() -> dict[Point, str]:
    pixels: dict[Point, str] = {}
    nodes = ((0, 0), (3, 0), (7, 0), (0, 4), (7, 3), (0, 7), (4, 7), (7, 7))
    for index, node in enumerate(nodes):
        pixels[node] = BRIGHT[index]
        target = (3, 3) if index < 4 else (4, 4)
        for point in _line(node, target):
            pixels.setdefault(point, DIM[index])
    for point in ((3, 3), (4, 3), (3, 4), (4, 4)):
        pixels[point] = WHITE
    return pixels


def _logo_pixels() -> dict[Point, ColorSpec]:
    pattern = (
        "11100100",
        "10010100",
        "10010100",
        "11100100",
        "10000100",
        "10000100",
        "10000100",
        "00000111",
    )
    pixels: dict[Point, ColorSpec] = {}
    for y, row in enumerate(pattern):
        for x, value in enumerate(row):
            if value == "1":
                color_index = (y + (0 if x < 4 else 4)) % len(BRIGHT)
                hue = 0.5 + 0.42 * x / (SHOW_WIDTH - 1) + 0.015 * y
                pixels[(x, y)] = _hsv_color(
                    BRIGHT[color_index],
                    hue,
                    0.78,
                    0.78 + 0.2 * (SHOW_HEIGHT - 1 - y) / (SHOW_HEIGHT - 1),
                )
    return pixels


def _dimmed(pixels: Pixels) -> dict[Point, ColorSpec]:
    replacements = {
        WHITE: WHITE_DIM,
        BLUE: BLUE_DIM,
        GREEN: GREEN_DIM,
        RED: RED_DIM,
        AMBER: AMBER_DIM,
        **DIM_TOKEN,
    }
    dimmed: dict[Point, ColorSpec] = {}
    for point, color in pixels.items():
        if isinstance(color, ShowColor):
            fallback = replacements.get(color.fallback, color.fallback)
            dimmed[point] = ShowColor(
                fallback,
                tuple(round(channel * 0.3) for channel in color.rgb),
            )
        else:
            dimmed[point] = replacements.get(color, color)
    return dimmed


def _line(start: Point, end: Point) -> tuple[Point, ...]:
    x1, y1 = start
    x2, y2 = end
    dx = abs(x2 - x1)
    sx = 1 if x1 < x2 else -1
    dy = -abs(y2 - y1)
    sy = 1 if y1 < y2 else -1
    error = dx + dy
    points: list[Point] = []
    while True:
        points.append((x1, y1))
        if x1 == x2 and y1 == y2:
            return tuple(points)
        twice_error = 2 * error
        if twice_error >= dy:
            error += dy
            x1 += sx
        if twice_error <= dx:
            error += dx
            y1 += sy
