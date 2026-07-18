from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from pad_lattice.schema_validation import (
    SchemaValidationError,
    SchemaValidationUnavailable,
    validate_json_schema,
)


class SchemaValidationTest(TestCase):
    def test_missing_optional_dependency_has_install_instruction(self) -> None:
        with (
            patch(
                "pad_lattice.schema_validation._load_validator_class",
                side_effect=SchemaValidationUnavailable("install schema extra"),
            ),
            self.assertRaisesRegex(
                SchemaValidationUnavailable,
                "install schema extra",
            ),
        ):
            validate_json_schema({}, {}, context="profile.json")

    def test_validation_error_includes_instance_path(self) -> None:
        class Error:
            absolute_path = ("grid", "rows", 2)
            message = "row is too short"

        class Validator:
            @classmethod
            def check_schema(cls, schema) -> None:
                pass

            def __init__(self, schema) -> None:
                pass

            def iter_errors(self, instance):
                return iter((Error(),))

        with (
            patch(
                "pad_lattice.schema_validation._load_validator_class",
                return_value=Validator,
            ),
            self.assertRaisesRegex(
                SchemaValidationError,
                r"profile.json: \$\.grid\.rows\[2\]: row is too short",
            ),
        ):
            validate_json_schema({}, {}, context="profile.json")
