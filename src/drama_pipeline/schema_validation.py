"""Dependency-free validator for the production-pack JSON Schema subset."""
from __future__ import annotations

import re
from typing import Any


def _resolve(root: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    reference = schema.get("$ref")
    if not reference:
        return schema
    if not reference.startswith("#/"):
        raise ValueError(f"Only local schema references are supported: {reference}")
    node: Any = root
    for key in reference[2:].split("/"):
        node = node[key.replace("~1", "/").replace("~0", "~")]
    return node


def _matches_type(value: Any, expected: str) -> bool:
    checks = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
    }
    return checks.get(expected, lambda _item: True)(value)


def _limits(value: Any, schema: dict[str, Any], path: str) -> list[str]:
    errors = []
    if isinstance(value, str):
        if len(value) < int(schema.get("minLength", 0)):
            errors.append(f"{path}: shorter than minLength")
        if schema.get("pattern") and not re.search(str(schema["pattern"]), value):
            errors.append(f"{path}: does not match {schema['pattern']}")
    if isinstance(value, list) and len(value) < int(schema.get("minItems", 0)):
        errors.append(f"{path}: fewer than minItems")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: above maximum {schema['maximum']}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: not in enum {schema['enum']}")
    return errors


def _object_errors(value: dict[str, Any], schema: dict[str, Any], root: dict[str, Any], path: str) -> list[str]:
    errors = []
    properties = schema.get("properties", {})
    for key in schema.get("required", []):
        if key not in value:
            errors.append(f"{path}.{key}: required property is missing")
    if schema.get("additionalProperties") is False:
        for key in value.keys() - properties.keys():
            errors.append(f"{path}.{key}: additional property is forbidden")
    for key, child in properties.items():
        if key in value:
            errors.extend(_validate(value[key], child, root, f"{path}.{key}"))
    return errors


def _array_errors(value: list[Any], schema: dict[str, Any], root: dict[str, Any], path: str) -> list[str]:
    child = schema.get("items")
    if not isinstance(child, dict):
        return []
    errors = []
    for index, item in enumerate(value):
        errors.extend(_validate(item, child, root, f"{path}[{index}]"))
    return errors


def _validate(value: Any, raw_schema: dict[str, Any], root: dict[str, Any], path: str) -> list[str]:
    schema = _resolve(root, raw_schema)
    expected = schema.get("type")
    if expected and not _matches_type(value, expected):
        return [f"{path}: expected {expected}, got {type(value).__name__}"]
    errors = _limits(value, schema, path)
    if expected == "object":
        errors.extend(_object_errors(value, schema, root, path))
    elif expected == "array":
        errors.extend(_array_errors(value, schema, root, path))
    return errors


def validate_instance(instance: Any, schema: dict[str, Any]) -> list[str]:
    """Return human-readable errors; an empty list means schema-valid."""
    return _validate(instance, schema, schema, "$")


def _selftest() -> None:
    schema = {
        "type": "object", "required": ["title", "beats"],
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string", "minLength": 3},
            "beats": {"type": "array", "minItems": 1,
                      "items": {"type": "integer", "minimum": 1}},
        },
    }
    assert validate_instance({"title": "Episode 1", "beats": [1, 2]}, schema) == []
    broken = validate_instance({"title": "x", "beats": [0], "extra": True}, schema)
    assert any("minLength" in item for item in broken)
    assert any("below minimum" in item for item in broken)
    assert any("additional property" in item for item in broken)
    print("schema_validation self-test GREEN")


if __name__ == "__main__":
    _selftest()
