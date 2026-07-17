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
    parse_profile,
)


def valid_profile_data() -> dict:
    profile = ProfileCatalog.load(include_user=False).get(
        "novation/launchpad/pro-mk1"
    )
    return json.loads(Path(profile.source).read_text(encoding="utf-8"))


class DeviceProfileTest(TestCase):
    def test_built_in_profiles_follow_manufacturer_family_model_hierarchy(self) -> None:
        catalog = ProfileCatalog.load(include_user=False)

        self.assertEqual(
            [profile.id for profile in catalog.profiles],
            [
                "novation/launchpad/mini-mk3",
                "novation/launchpad/pro-mk1",
            ],
        )
        self.assertEqual(catalog.get("novation/launchpad/pro-mk1").status, "supported")
        self.assertEqual(
            catalog.get("novation/launchpad/mini-mk3").status,
            "experimental",
        )

    def test_profiles_define_four_multi_agent_slots(self) -> None:
        catalog = ProfileCatalog.load(include_user=False)

        for profile in catalog.profiles:
            with self.subTest(profile=profile.id):
                self.assertEqual(profile.selector_capacity, 4)
                self.assertEqual(
                    [address.number for address in profile.selectors],
                    [13, 14, 15, 16],
                )
                self.assertEqual([address.number for address in profile.statuses], [23, 24, 25, 26])

    def test_mini_profile_restores_live_mode_on_shutdown(self) -> None:
        profile = ProfileCatalog.load(include_user=False).get(
            "novation/launchpad/mini-mk3"
        )

        self.assertEqual(profile.startup[0].data, (0, 32, 41, 2, 13, 14, 1))
        self.assertEqual(profile.shutdown[0].data, (0, 32, 41, 2, 13, 14, 0))

    def test_profile_file_loader_reports_invalid_json(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            path.write_text("not-json", encoding="utf-8")

            with self.assertRaisesRegex(ProfileError, "invalid JSON"):
                load_profile_file(path)

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
        data["controls"]["statuses"].pop()

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

        with self.assertRaisesRegex(ProfileError, "exactly 4 color pairs"):
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
        self.assertIn("Live Port", candidates[0].input_name)
        self.assertIn("Live Port", candidates[0].output_name)

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
