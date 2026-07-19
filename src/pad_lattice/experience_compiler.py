"""Deterministically compile authored experiences for every runtime."""

from __future__ import annotations

import argparse
import filecmp
import json
import tempfile
from pathlib import Path

from pad_lattice.audio import (
    REFERENCE_SCORE_BEATS,
    ROBOT_GREETING_TEXT,
    Earcon,
    _constellation_score,
    _write_earcon,
    _write_robot_speech,
    _write_stereo_wav,
)
from pad_lattice.experience_manifest import load_performance_data
from pad_lattice.show import _author_constellation_show, _story_timeline

PERFORMANCE_FILENAME = "constellation-v1.json"
SOUNDTRACK_FILENAME = "constellation-v1.wav"
GREETING_FILENAME = "greeting.wav"


def compile_experience_assets(target: Path) -> None:
    """Write the canonical manifest and browser audio bank."""

    target.mkdir(parents=True, exist_ok=True)
    audio_target = target / "audio"
    audio_target.mkdir(parents=True, exist_ok=True)
    cues = _author_constellation_show()
    manifest = _performance_manifest(cues)
    load_performance_data(manifest, source="compiled performance")
    (target / PERFORMANCE_FILENAME).write_text(
        json.dumps(manifest, separators=(",", ":"), ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    _write_soundtrack(audio_target / SOUNDTRACK_FILENAME, cues)
    _write_robot_speech(audio_target / GREETING_FILENAME, ROBOT_GREETING_TEXT, 10.32)
    for cue in Earcon:
        for slot in (None, *range(8)):
            suffix = "none" if slot is None else str(slot)
            _write_earcon(audio_target / f"earcon-{cue.value}-{suffix}.wav", cue, slot)


def check_experience_assets(target: Path) -> tuple[str, ...]:
    """Return changed or missing generated paths without modifying the target."""

    with tempfile.TemporaryDirectory(prefix="pad-lattice-experiences-") as directory:
        generated = Path(directory)
        compile_experience_assets(generated)
        differences: list[str] = []
        expected = {
            path.relative_to(generated)
            for path in generated.rglob("*")
            if path.is_file()
        }
        actual = {
            path.relative_to(target)
            for path in target.rglob("*")
            if path.is_file() and path.name != "demo-v1.json"
        } if target.exists() else set()
        for relative in sorted(expected | actual):
            generated_path = generated / relative
            target_path = target / relative
            if not generated_path.is_file() or not target_path.is_file():
                differences.append(str(relative))
            elif not filecmp.cmp(generated_path, target_path, shallow=False):
                differences.append(str(relative))
        return tuple(differences)


def _performance_manifest(cues) -> dict[str, object]:
    colors = sorted(
        {
            (color.fallback, color.rgb)
            for cue in cues
            for color in (
                *(color for row in cue.frame.grid for color in row),
                *cue.frame.top,
                *cue.frame.right,
            )
        }
    )
    palette_index = {color: index for index, color in enumerate(colors)}
    acts = tuple(dict.fromkeys(cue.act for cue in cues))
    act_index = {act: index for index, act in enumerate(acts)}
    duration_ms = sum(round(cue.duration * 1000) for cue in cues)

    def color_id(color) -> int:
        return palette_index[(color.fallback, color.rgb)]

    return {
        "schema_version": 1,
        "kind": "performance",
        "id": "a-spark-becomes-a-constellation",
        "title": "A Spark Becomes a Constellation",
        "dimensions": {"grid": [8, 8], "top": 8, "right": 8},
        "duration_ms": duration_ms,
        "acts": list(acts),
        "palette": [
            {"fallback": fallback, "rgb": list(rgb)}
            for fallback, rgb in colors
        ],
        "cues": [
            {
                "act": act_index[cue.act],
                "duration_ms": round(cue.duration * 1000),
                "caption": cue.caption,
                "frame": {
                    "grid": [
                        [color_id(color) for color in row]
                        for row in cue.frame.grid
                    ],
                    "top": [color_id(color) for color in cue.frame.top],
                    "right": [color_id(color) for color in cue.frame.right],
                },
            }
            for cue in cues
        ],
        "audio": {
            "asset": f"audio/{SOUNDTRACK_FILENAME}",
            "mime_type": "audio/wav",
            "duration_ms": duration_ms,
        },
    }


def _write_soundtrack(path: Path, cues) -> None:
    timeline = _story_timeline(cues, tempo=1.0)
    duration = max(beat.start + beat.duration for beat in timeline)
    tones, noises, speeches = _constellation_score(timeline, duration)
    _write_stereo_wav(
        path,
        duration,
        tones,
        noises,
        speeches,
        beat_length=(duration - timeline[0].start) / REFERENCE_SCORE_BEATS,
    )


def _default_target() -> Path:
    return Path(__file__).resolve().parents[2] / "web-app" / "public" / "experiences"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="regenerate committed assets")
    mode.add_argument("--check", action="store_true", help="verify committed assets")
    parser.add_argument("--target", type=Path, default=_default_target())
    args = parser.parse_args(argv)
    if args.write:
        compile_experience_assets(args.target)
        return 0
    differences = check_experience_assets(args.target)
    if differences:
        print("Generated experience assets are stale:")
        for path in differences:
            print(f"  {path}")
        return 1
    print("Generated experience assets are current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
