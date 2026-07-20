from __future__ import annotations

import copy
import json
from pathlib import Path
from unittest import TestCase, skipUnless

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - optional schema extra
    Draft202012Validator = None  # type: ignore[assignment]

from pad_lattice.experience_manifest import (
    ExperienceManifestError,
    load_builtin_demo,
    load_builtin_performance,
    load_demo_data,
    load_demo_schema,
    load_performance_data,
    load_performance_schema,
)


class ExperienceManifestTest(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path("web-app/public/experiences")
        cls.performance_data = json.loads(
            (root / "constellation-v1.json").read_text(encoding="utf-8")
        )
        cls.demo_data = json.loads(
            (root / "demo-v1.json").read_text(encoding="utf-8")
        )

    def test_builtin_experiences_share_the_version_one_contract(self) -> None:
        performance = load_builtin_performance()
        demo = load_builtin_demo()

        self.assertEqual(performance.schema_version, 1)
        self.assertEqual(len(performance.cues), 80)
        self.assertAlmostEqual(performance.duration, 43.1)
        self.assertEqual(demo.schema_version, 1)
        self.assertEqual(len(demo.stages), 6)
        self.assertEqual(demo.stage(demo.initial_stage).id, "select_reviewer")
        self.assertEqual(demo.stage(demo.initial_stage).guide_target.slot, 1)

        question_index = next(
            index
            for index, cue in enumerate(performance.cues)
            if cue.caption == "A question"
        )
        self.assertEqual(performance.caption_at(question_index + 1), "A question")

    def test_performance_rejects_bad_dimensions_and_palette_references(self) -> None:
        bad_dimensions = copy.deepcopy(self.performance_data)
        bad_dimensions["dimensions"]["grid"] = [7, 8]
        with self.assertRaisesRegex(ExperienceManifestError, "8x8 grid"):
            load_performance_data(bad_dimensions, source="bad-performance")

        bad_palette = copy.deepcopy(self.performance_data)
        bad_palette["cues"][0]["frame"]["grid"][0][0] = len(
            bad_palette["palette"]
        )
        with self.assertRaisesRegex(ExperienceManifestError, "outside the palette"):
            load_performance_data(bad_palette, source="bad-performance")

    def test_demo_rejects_unknown_transition_targets(self) -> None:
        bad_demo = copy.deepcopy(self.demo_data)
        bad_demo["stages"][0]["transitions"][0]["next_stage"] = "missing"

        with self.assertRaisesRegex(ExperienceManifestError, "unknown stage"):
            load_demo_data(bad_demo, source="bad-demo")

    def test_demo_guide_target_must_match_a_transition(self) -> None:
        bad_demo = copy.deepcopy(self.demo_data)
        bad_demo["stages"][0]["guide_target"]["slot"] = 2

        with self.assertRaisesRegex(ExperienceManifestError, "guide target"):
            load_demo_data(bad_demo, source="bad-demo")

    @skipUnless(Draft202012Validator is not None, "install pad-lattice[schema]")
    def test_source_assets_validate_against_the_published_schemas(self) -> None:
        Draft202012Validator(load_performance_schema()).validate(
            self.performance_data
        )
        Draft202012Validator(load_demo_schema()).validate(self.demo_data)
