# -*- coding: utf-8 -*-
"""Self-authored deterministic vector-scene compiler.

The compiler emits standards-based SVG for a small audited primitive set.
Rasterization/encoding can then be handled by a browser, FFmpeg or another
low-level engine without changing Hao's scene schema.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


SCHEMA = "hao.vector-scene/v1"
PRIMITIVES = {"rect", "circle", "line", "path", "text", "group"}


def validate_scene(scene: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if scene.get("schema") != SCHEMA:
        errors.append(f"schema must equal {SCHEMA}")
    for key in ("width", "height"):
        if not isinstance(scene.get(key), int) or int(scene[key]) <= 0:
            errors.append(key + " must be a positive integer")
    for index, item in enumerate(scene.get("items") or []):
        if item.get("type") not in PRIMITIVES:
            errors.append(f"items[{index}].type is unsupported")
        if item.get("type") == "path" and not str(item.get("d", "")).strip():
            errors.append(f"items[{index}].d is required")
    return errors


def _attributes(item: dict[str, Any], excluded: set[str]) -> str:
    attributes = []
    for key, value in sorted(item.items()):
        if key in excluded or value is None:
            continue
        name = "class" if key == "class_name" else key.replace("_", "-")
        attributes.append(f'{html.escape(name)}="{html.escape(str(value), quote=True)}"')
    return " ".join(attributes)


def _item_svg(item: dict[str, Any]) -> str:
    kind = item["type"]
    if kind == "group":
        attrs = _attributes(item, {"type", "items"})
        children = "".join(_item_svg(child) for child in item.get("items") or [])
        return f"<g {attrs}>{children}</g>" if attrs else f"<g>{children}</g>"
    if kind == "text":
        attrs = _attributes(item, {"type", "text"})
        return f"<text {attrs}>{html.escape(str(item.get('text', '')))}</text>"
    attrs = _attributes(item, {"type"})
    return f"<{kind} {attrs}/>"


def compile_svg(scene: dict[str, Any]) -> str:
    errors = validate_scene(scene)
    if errors:
        raise ValueError("invalid vector scene: " + "; ".join(errors))
    children = "".join(_item_svg(item) for item in scene.get("items") or [])
    width, height = int(scene["width"]), int(scene["height"])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">{children}</svg>\n'
    )


def self_test() -> None:
    scene = {
        "schema": SCHEMA, "width": 1080, "height": 1920,
        "items": [{"type": "rect", "x": 10, "y": 20, "width": 30, "height": 40, "fill": "#fff"},
                  {"type": "text", "x": 80, "y": 120, "text": "AI & 教學"}],
    }
    svg = compile_svg(scene)
    assert "AI &amp; 教學" in svg and "viewBox" in svg
    print("vector_scene_runtime self-test GREEN")


def main() -> int:
    parser = argparse.ArgumentParser(description="Hao deterministic vector-scene compiler")
    parser.add_argument("command", choices=("validate", "compile", "selftest"))
    parser.add_argument("scene", nargs="?")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.command == "selftest":
        self_test()
        return 0
    if not args.scene:
        parser.error("scene is required")
    scene = json.loads(Path(args.scene).read_text(encoding="utf-8"))
    if args.command == "validate":
        errors = validate_scene(scene)
        print(json.dumps({"status": "GREEN" if not errors else "BLOCK", "errors": errors}, ensure_ascii=False, indent=2))
        return 0 if not errors else 2
    payload = compile_svg(scene)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
