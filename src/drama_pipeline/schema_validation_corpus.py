"""Real-schema regression for the dependency-free production-pack validator."""
from __future__ import annotations

import json

from .planner import schema_path
from .schema_validation import validate_instance


def main() -> None:
    production_schema = json.loads(schema_path().read_text(encoding="utf-8"))
    identifier_schema = {
        "$defs": production_schema["$defs"],
        "$ref": "#/$defs/identifier",
    }
    assert validate_instance("hero_01", identifier_schema) == []
    assert validate_instance("Hero 01", identifier_schema)

    nonempty_schema = {
        "$defs": production_schema["$defs"],
        "$ref": "#/$defs/nonempty",
    }
    assert validate_instance("真實製作文字", nonempty_schema) == []
    assert validate_instance("", nonempty_schema)
    print("schema_validation corpus GREEN")


if __name__ == "__main__":
    main()
