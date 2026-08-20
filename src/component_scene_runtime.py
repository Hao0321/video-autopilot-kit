# -*- coding: utf-8 -*-
"""Self-authored deterministic component-scene evaluator.

This module is the application-layer animation runtime.  It evaluates reusable
scene components at an integer frame and returns an immutable render state.
Pixel encoding remains delegated to low-level engines such as FFmpeg, Pillow,
OpenCV or a browser renderer.
"""
from __future__ import annotations

import argparse
import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any


SCHEMA = "hao.component-scene/v1"
EASINGS = {"linear", "ease_in", "ease_out", "ease_in_out", "spring_soft"}


def _ease(progress: float, name: str) -> float:
    p = max(0.0, min(1.0, progress))
    if name == "ease_in":
        return p * p
    if name == "ease_out":
        return 1.0 - (1.0 - p) ** 3
    if name == "ease_in_out":
        return p * p * (3.0 - 2.0 * p)
    if name == "spring_soft":
        return 1.0 - math.exp(-6.0 * p) * math.cos(7.5 * p)
    return p


def _interpolate(left: Any, right: Any, progress: float) -> Any:
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left + (right - left) * progress
    if (isinstance(left, list) and isinstance(right, list) and
            len(left) == len(right) and all(isinstance(v, (int, float)) for v in left + right)):
        return [_interpolate(a, b, progress) for a, b in zip(left, right)]
    return right if progress >= 1.0 else left


def evaluate_keyframes(rows: list[dict[str, Any]], frame: int) -> Any:
    """Evaluate ordered keyframes without consulting wall-clock time."""
    if not rows:
        raise ValueError("keyframe list must not be empty")
    ordered = sorted(rows, key=lambda row: int(row["frame"]))
    if frame <= int(ordered[0]["frame"]):
        return deepcopy(ordered[0]["value"])
    if frame >= int(ordered[-1]["frame"]):
        return deepcopy(ordered[-1]["value"])
    for left, right in zip(ordered, ordered[1:]):
        a, b = int(left["frame"]), int(right["frame"])
        if a <= frame <= b:
            progress = (frame - a) / max(1, b - a)
            progress = _ease(progress, str(right.get("easing", "linear")))
            return _interpolate(left["value"], right["value"], progress)
    return deepcopy(ordered[-1]["value"])


def validate_scene(scene: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if scene.get("schema") != SCHEMA:
        errors.append(f"schema must equal {SCHEMA}")
    if not str(scene.get("id", "")).strip():
        errors.append("id is required")
    duration = scene.get("duration_frames")
    if not isinstance(duration, int) or duration <= 0:
        errors.append("duration_frames must be a positive integer")
        duration = 0
    nodes = scene.get("nodes")
    if not isinstance(nodes, list):
        return errors + ["nodes must be a list"]
    ids: set[str] = set()
    for index, node in enumerate(nodes):
        prefix = f"nodes[{index}]"
        node_id = str(node.get("id", "")).strip()
        if not node_id:
            errors.append(prefix + ".id is required")
        elif node_id in ids:
            errors.append(prefix + ".id must be unique")
        ids.add(node_id)
        start = int(node.get("start_frame", 0))
        node_duration = int(node.get("duration_frames", 0))
        if start < 0 or node_duration <= 0 or start + node_duration > duration:
            errors.append(prefix + " must fit scene frame bounds")
        animations = node.get("animations") or {}
        if not isinstance(animations, dict):
            errors.append(prefix + ".animations must be an object")
            continue
        for property_name, rows in animations.items():
            if not isinstance(rows, list) or not rows:
                errors.append(prefix + f".animations.{property_name} must contain keyframes")
                continue
            for row in rows:
                if not isinstance(row.get("frame"), int) or "value" not in row:
                    errors.append(prefix + f".animations.{property_name} keyframes require integer frame and value")
                if str(row.get("easing", "linear")) not in EASINGS:
                    errors.append(prefix + f".animations.{property_name} has unsupported easing")
    return errors


def evaluate_scene(scene: dict[str, Any], frame: int) -> dict[str, Any]:
    errors = validate_scene(scene)
    if errors:
        raise ValueError("invalid component scene: " + "; ".join(errors))
    if not 0 <= frame < int(scene["duration_frames"]):
        raise ValueError("frame is outside scene bounds")
    active: list[dict[str, Any]] = []
    for node in sorted(scene["nodes"], key=lambda row: (int(row.get("z", 0)), str(row["id"]))):
        start = int(node.get("start_frame", 0))
        end = start + int(node["duration_frames"])
        if not start <= frame < end:
            continue
        local_frame = frame - start
        props = deepcopy(node.get("props") or {})
        for property_name, rows in (node.get("animations") or {}).items():
            props[property_name] = evaluate_keyframes(rows, local_frame)
        active.append({
            "id": node["id"], "component": node.get("component", "group"),
            "z": int(node.get("z", 0)), "local_frame": local_frame,
            "progress": local_frame / max(1, int(node["duration_frames"]) - 1),
            "props": props,
        })
    return {"status": "GREEN", "scene_id": scene["id"], "frame": frame, "nodes": active}


def self_test() -> None:
    scene = {
        "schema": SCHEMA, "id": "test", "duration_frames": 30,
        "nodes": [{
            "id": "title", "component": "text", "start_frame": 3,
            "duration_frames": 20, "z": 2, "props": {"text": "測試"},
            "animations": {
                "opacity": [{"frame": 0, "value": 0}, {"frame": 5, "value": 1, "easing": "ease_out"}],
                "position": [{"frame": 0, "value": [0, 20]}, {"frame": 5, "value": [0, 0]}],
            },
        }],
    }
    assert validate_scene(scene) == []
    assert evaluate_scene(scene, 2)["nodes"] == []
    state = evaluate_scene(scene, 6)
    assert state["nodes"][0]["local_frame"] == 3
    assert 0 < state["nodes"][0]["props"]["opacity"] < 1
    print("component_scene_runtime self-test GREEN")


def main() -> int:
    parser = argparse.ArgumentParser(description="Hao deterministic component-scene runtime")
    parser.add_argument("command", choices=("validate", "evaluate", "selftest"))
    parser.add_argument("scene", nargs="?")
    parser.add_argument("--frame", type=int, default=0)
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
    print(json.dumps(evaluate_scene(scene, args.frame), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
