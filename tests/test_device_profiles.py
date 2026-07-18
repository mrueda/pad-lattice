from __future__ import annotations

import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from pad_lattice.devices.factory import resolve_device
from pad_lattice.devices.profiles import (
    ProfileCatalog,
    ProfileError,
    load_profile_file,
    load_profile_schema,
    parse_profile,
)
from pad_lattice.events import ControlAction
from pad_lattice.visual_protocol import VISUAL_PROTOCOL_VERSION


def valid_profile_data() -> dict:
    profile = ProfileCatalog.load(include_user=False).get(
        "novation/launchpad/pro-mk1"
    )
    return json.loads(Path(profile.source).read_text(encoding="utf-8"))


class DeviceProfileTest(TestCase):
    def test_machine_readable_schema_is_packaged(self) -> None:
        schema = load_profile_schema()

        self.assertEqual(schema["title"], "Pad-Lattice Device Profile v1")
        self.assertEqual(schema["properties"]["schema_version"]["const"], 1)
        self.assertEqual(
            schema["properties"]["visual_protocol"]["const"],
            VISUAL_PROTOCOL_VERSION,
        )

    def test_built_in_profiles_follow_manufacturer_family_model_hierarchy(self) -> None:
        catalog = ProfileCatalog.load(include_user=False)

        self.assertEqual(
            [profile.id for profile in catalog.profiles],
            [
                "novation/launchpad/mini-mk3",
                "novation/launchpad/pro-mk1",
                "novation/launchpad/pro-mk3",
            ],
        )
        self.assertEqual(catalog.get("novation/launchpad/pro-mk1").status, "supported")
        self.assertEqual(
            catalog.get("novation/launchpad/pro-mk1").name,
            "Novation Launchpad Pro Mk1",
        )
        self.assertEqual(
            catalog.get("novation/launchpad/mini-mk3").status,
            "experimental",
        )
        self.assertEqual(
            catalog.get("novation/launchpad/pro-mk3").status,
            "experimental",
        )

    def test_profiles_define_eight_multi_agent_slots(self) -> None:
        catalog = ProfileCatalog.load(include_user=False)

        for profile in catalog.profiles:
            with self.subTest(profile=profile.id):
                self.assertEqual(profile.schema_version, 1)
                self.assertEqual(profile.visual_protocol, 1)
                self.assertEqual(profile.selector_capacity, 8)
                self.assertEqual(
                    [address.number for address in profile.selectors],
                    [89, 79, 69, 59, 49, 39, 29, 19],
                )
                self.assertEqual(
                    [address.number for address in profile.statuses],
                    [88, 78, 68, 58, 48, 38, 28, 18],
                )
                self.assertEqual(profile.state_region.x, 0)
                self.assertEqual(profile.state_region.y, 0)
                self.assertEqual(profile.state_region.width, 7)
                self.assertEqual(profile.state_region.height, 8)
                self.assertEqual(
                    profile.conformance,
                    frozenset({"core-state", "multi-agent", "actions"}),
                )

    def test_pro_profile_uses_standalone_programmer_mode(self) -> None:
        profile = ProfileCatalog.load(include_user=False).get(
            "novation/launchpad/pro-mk1"
        )

        self.assertIn("Standalone Port", profile.input_patterns[0])
        self.assertEqual(profile.startup[0].data, (0, 32, 41, 2, 16, 33, 1))
        self.assertEqual(profile.startup[1].data, (0, 32, 41, 2, 16, 44, 3))
        self.assertEqual(profile.shutdown[-1].data, (0, 32, 41, 2, 16, 33, 0))
        self.assertEqual(
            {
                action: profile.controls[action].number
                for action in ControlAction
            },
            {
                ControlAction.APPROVE: 91,
                ControlAction.REJECT: 92,
                ControlAction.RETRY: 97,
                ControlAction.STOP: 98,
            },
        )
        self.assertEqual(
            {address.kind for address in profile.controls.values()},
            {"cc"},
        )

    def test_mini_profile_restores_live_mode_on_shutdown(self) -> None:
        profile = ProfileCatalog.load(include_user=False).get(
            "novation/launchpad/mini-mk3"
        )

        self.assertEqual(profile.startup[0].data, (0, 32, 41, 2, 13, 14, 1))
        self.assertEqual(profile.shutdown[0].data, (0, 32, 41, 2, 13, 14, 0))
        self.assertEqual(
            {
                action: profile.controls[action].number
                for action in ControlAction
            },
            {
                ControlAction.APPROVE: 91,
                ControlAction.REJECT: 92,
                ControlAction.RETRY: 97,
                ControlAction.STOP: 98,
            },
        )
        self.assertEqual(
            {address.kind for address in profile.controls.values()},
            {"cc"},
        )

    def test_pro_mk3_profile_uses_documented_programmer_mode(self) -> None:
        profile = ProfileCatalog.load(include_user=False).get(
            "novation/launchpad/pro-mk3"
        )

        self.assertEqual(profile.status, "experimental")
        self.assertEqual(profile.startup[0].data, (0, 32, 41, 2, 14, 14, 1))
        self.assertEqual(profile.shutdown[0].data, (0, 32, 41, 2, 14, 14, 0))
        self.assertEqual(
            {
                action: profile.controls[action].number
                for action in ControlAction
            },
            {
                ControlAction.APPROVE: 91,
                ControlAction.REJECT: 92,
                ControlAction.RETRY: 97,
                ControlAction.STOP: 98,
            },
        )

    def test_pro_mk3_detection_prefers_midi_interface(self) -> None:
        catalog = ProfileCatalog.load(include_user=False)

        candidates = catalog.detect(
            [
                "LPProMK3 DIN 20:0",
                "LPProMK3 MIDI 2 20:1",
                "LPProMK3 DAW 20:2",
            ],
            [
                "LPProMK3 DIN 20:0",
                "LPProMK3 MIDI 2 20:1",
                "LPProMK3 DAW 20:2",
            ],
        )

        pro_mk3 = [
            candidate
            for candidate in candidates
            if candidate.profile.id == "novation/launchpad/pro-mk3"
        ]
        self.assertEqual(len(pro_mk3), 1)
        self.assertEqual(pro_mk3[0].input_name, "LPProMK3 MIDI 2 20:1")
        self.assertEqual(pro_mk3[0].output_name, "LPProMK3 MIDI 2 20:1")

    def test_profile_file_loader_reports_invalid_json(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            path.write_text("not-json", encoding="utf-8")

            with self.assertRaisesRegex(ProfileError, "invalid JSON"):
                load_profile_file(path)

    def test_profile_schema_validation_is_explicit_opt_in(self) -> None:
        profile = ProfileCatalog.load(include_user=False).get(
            "novation/launchpad/pro-mk3"
        )
        path = Path(profile.source)

        with patch(
            "pad_lattice.devices.profiles.validate_json_schema"
        ) as validate:
            load_profile_file(path)
            validate.assert_not_called()

            load_profile_file(path, validate_schema=True)
            validate.assert_called_once()

    def test_profile_rejects_unknown_driver(self) -> None:
        data = valid_profile_data()
        data["driver"] = "third-party.untrusted"

        with self.assertRaisesRegex(ProfileError, "unknown driver"):
            parse_profile(data)

    def test_profile_rejects_invalid_hierarchy_id(self) -> None:
        data = valid_profile_data()
        data["id"] = "Launchpad Pro"

        with self.assertRaisesRegex(ProfileError, "manufacturer/family/model"):
            parse_profile(data)

    def test_profile_requires_matching_selector_and_status_counts(self) -> None:
        data = valid_profile_data()
        data["surface"]["agent_statuses"].pop()

        with self.assertRaisesRegex(ProfileError, "equal lengths"):
            parse_profile(data)

    def test_profile_id_must_match_metadata_hierarchy(self) -> None:
        data = valid_profile_data()
        data["model"] = "Different Model"

        with self.assertRaisesRegex(ProfileError, "does not match profile metadata"):
            parse_profile(data)

    def test_profile_rejects_duplicate_grid_addresses(self) -> None:
        data = valid_profile_data()
        data["grid"]["rows"][0][1] = data["grid"]["rows"][0][0]

        with self.assertRaisesRegex(ProfileError, "duplicate MIDI address"):
            parse_profile(data)

    def test_profile_requires_one_accent_per_selector(self) -> None:
        data = valid_profile_data()
        data["accents"].pop()

        with self.assertRaisesRegex(ProfileError, "exactly 8 named color pairs"):
            parse_profile(data)

    def test_profile_rejects_unknown_visual_protocol(self) -> None:
        data = valid_profile_data()
        data["visual_protocol"] = 9

        with self.assertRaisesRegex(ProfileError, "unsupported visual_protocol"):
            parse_profile(data)

    def test_profile_rejects_state_control_overlap(self) -> None:
        data = valid_profile_data()
        data["surface"]["actions"]["approve"] = {"kind": "note", "number": 71}

        with self.assertRaisesRegex(ProfileError, "state region overlaps"):
            parse_profile(data)

    def test_multi_agent_conformance_requires_overflow_indicator(self) -> None:
        data = valid_profile_data()
        del data["surface"]["indicators"]["overflow"]

        with self.assertRaisesRegex(ProfileError, "requires an overflow indicator"):
            parse_profile(data)

    def test_catalog_rejects_duplicate_ids(self) -> None:
        profile = ProfileCatalog.load(include_user=False).get(
            "novation/launchpad/pro-mk1"
        )

        with self.assertRaisesRegex(ProfileError, "duplicate profile id"):
            ProfileCatalog([profile, copy.copy(profile)])

    def test_detection_uses_first_matching_port_pattern(self) -> None:
        catalog = ProfileCatalog.load(include_user=False)

        candidates = catalog.detect(
            [
                "Launchpad Pro:Launchpad Pro Standalone Port 20:1",
                "Launchpad Pro:Launchpad Pro Live Port 20:0",
            ],
            [
                "Launchpad Pro:Launchpad Pro Standalone Port 20:1",
                "Launchpad Pro:Launchpad Pro Live Port 20:0",
            ],
            include_experimental=False,
        )

        self.assertEqual(len(candidates), 1)
        self.assertIn("Standalone Port", candidates[0].input_name)
        self.assertIn("Standalone Port", candidates[0].output_name)

    def test_explicit_ports_do_not_trigger_midi_discovery(self) -> None:
        catalog = ProfileCatalog.load(include_user=False)

        with patch(
            "pad_lattice.devices.factory.list_midi_ports",
            side_effect=AssertionError("unexpected discovery"),
        ):
            device = resolve_device(
                profile_id="novation/launchpad/pro-mk1",
                input_name="Explicit input",
                output_name="Explicit output",
                catalog=catalog,
            )

        self.assertEqual(device.input_name, "Explicit input")
        self.assertEqual(device.output_name, "Explicit output")
