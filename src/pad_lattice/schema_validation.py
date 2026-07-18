"""Optional JSON Schema validation for authoring-time checks."""

from __future__ import annotations

from typing import Any


class SchemaValidationError(ValueError):
    """Raised when an instance does not conform to its published schema."""


class SchemaValidationUnavailable(ValueError):
    """Raised when optional schema tooling is not installed."""


def validate_json_schema(
    instance: Any,
    schema: dict[str, Any],
    *,
    context: str,
) -> None:
    """Validate one instance without making jsonschema a runtime dependency."""

    validator_class = _load_validator_class()
    validator_class.check_schema(schema)
    validator = validator_class(schema)
    error = next(validator.iter_errors(instance), None)
    if error is None:
        return
    location = "$"
    for item in error.absolute_path:
        location += f"[{item}]" if isinstance(item, int) else f".{item}"
    raise SchemaValidationError(f"{context}: {location}: {error.message}")


def _load_validator_class() -> type[Any]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise SchemaValidationUnavailable(
            "JSON Schema validation requires: pip install 'pad-lattice[schema]'"
        ) from exc
    return Draft202012Validator
