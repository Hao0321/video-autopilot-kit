# -*- coding: utf-8 -*-
"""Resolve Imagegen filter materials through the Asset Workshop review gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from project_paths import discover_project_root


ROOT = Path(__file__).resolve().parent
_PROJECT_KNOWLEDGE = ROOT / "knowledge"
_PUBLIC_KNOWLEDGE = ROOT.parent / "knowledge" / "runtime"
KNOWLEDGE_ROOT = (_PROJECT_KNOWLEDGE if _PROJECT_KNOWLEDGE.exists() else
                  _PUBLIC_KNOWLEDGE)
LIBRARY_PATH = KNOWLEDGE_ROOT / "filter_materials.json"


def load_library() -> dict[str, Any]:
    return json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))


def _workshop_manifest(project_root: Path) -> dict[str, Any]:
    path = project_root / "assets" / "workshop" / "manifest.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {"taste_boards": []}


def material_state(material_id: str, *, project_root: Path | None = None) -> dict[str, Any]:
    library = load_library()
    material = library.get("materials", {}).get(material_id)
    if material is None:
        raise KeyError("unknown filter material: " + material_id)
    root = project_root or discover_project_root(ROOT, required=False)
    if root is None:
        return {"material_id": material_id, "status": "IMAGEGEN_REQUIRED",
                "human_review": "missing", "selectable": False,
                "reason": "workspace not available", **material}
    path = root / material["path"]
    boards = _workshop_manifest(root).get("taste_boards", [])
    review = next((row for row in boards
                   if row.get("id") == material.get("taste_board_id")), {})
    human_review = review.get("human_review", "missing")
    approved = human_review == "approved" and path.is_file()
    return {"material_id": material_id,
            "status": "READY" if approved else "IMAGEGEN_REQUIRED",
            "human_review": human_review, "selectable": approved,
            "exists": path.is_file(), "absolute_path": str(path), **material}


def resolve_material(material_id: str, *, allow_pending: bool = False,
                     variant: int = 0) -> dict[str, Any]:
    state = material_state(material_id)
    pending_candidate = (allow_pending and state["exists"] and
                         state["human_review"] == "pending")
    if state["status"] != "READY" and not pending_candidate:
        return {**state, "render_status": "IMAGEGEN_REQUIRED",
                "render_fallback": "clean_hold", "image": None}
    image = cv2.imread(state["absolute_path"], cv2.IMREAD_COLOR)
    if image is None:
        return {**state, "render_status": "IMAGEGEN_REQUIRED",
                "render_fallback": "clean_hold", "image": None}
    rows, cols = state["layout"]
    count = rows * cols
    index = int(variant) % count
    row, column = divmod(index, cols)
    top = round(row * image.shape[0] / rows)
    bottom = round((row + 1) * image.shape[0] / rows)
    left = round(column * image.shape[1] / cols)
    right = round((column + 1) * image.shape[1] / cols)
    return {**state, "render_status": "CANDIDATE" if pending_candidate else "READY",
            "render_fallback": None, "variant": index,
            "image": image[top:bottom, left:right].copy()}


def validate_library() -> list[str]:
    data = load_library()
    errors = []
    if data.get("schema_version") != 1:
        errors.append("schema_version must equal 1")
    for material_id, material in data.get("materials", {}).items():
        if not material.get("taste_board_id") or not material.get("path"):
            errors.append(material_id + " requires taste_board_id and path")
        layout = material.get("layout") or []
        if len(layout) != 2 or min(layout) < 1:
            errors.append(material_id + " has invalid atlas layout")
    return errors


def self_test() -> None:
    assert not validate_library(), validate_library()
    assert len(load_library()["materials"]) >= 6
    for material_id in load_library()["materials"]:
        state = material_state(material_id)
        assert state["status"] in {"READY", "IMAGEGEN_REQUIRED"}
        if state["human_review"] != "approved":
            assert not state["selectable"]
    print("filter_materials self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect reviewed filter materials")
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect")
    inspect.add_argument("material_id")
    inspect.add_argument("--allow-pending", action="store_true")
    inspect.add_argument("--variant", type=int, default=0)
    sub.add_parser("list")
    sub.add_parser("selftest")
    args = parser.parse_args(argv)
    if args.command == "selftest":
        self_test()
        return 0
    if args.command == "list":
        result = [material_state(value) for value in load_library()["materials"]]
    else:
        result = resolve_material(args.material_id, allow_pending=args.allow_pending,
                                  variant=args.variant)
        result.pop("image", None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
