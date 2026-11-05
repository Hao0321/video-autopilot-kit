"""Long-form chapter helpers: chapter lookup, plan paths, expected receipts, refused commands, frame bounds."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from workflow_primitives import WorkflowError, material_for, require_list, require_mapping


REFUSED_COMMANDS = {"relink_asset_source": "LONGFORM_V1_RELINK_REFUSED",
                    "revise_original_motion_scene_graphic": "LONGFORM_V1_OWNER_REVISION_REFUSED"}

def chapter_for(state: dict[str, Any], step: dict[str, Any]) -> dict[str, Any]:
    for chapter in state["binding"]["longform_session"]["chapters"]:
        if chapter["key"] == step.get("chapter_key"):
            return chapter
    raise WorkflowError(f"LONGFORM_UNKNOWN_CHAPTER: {step.get('chapter_key')!r}")

def chapter_plan_path(state: dict[str, Any], chapter: dict[str, Any]) -> Path:
    return Path(state["run_dir"]) / "plans" / f"{chapter['key']}.v4.json"

def plan_set_path(state: dict[str, Any]) -> Path:
    return Path(state["run_dir"]) / "plan-set.json"

def expected_chapter_receipts(state: dict[str, Any], chapter: dict[str, Any]) -> list[dict[str, Any]]:
    from workflow_material_receipts import semantic_facts
    rows = []
    for key in chapter["material_keys"]:
        facts = semantic_facts(state, material_for(state, key))
        rows.append({"materialId": facts["material_id"], "sourceSha256": facts["source_sha256"],
                     "assetId": facts["asset_id"], "clipId": facts["clip_id"],
                     "semanticReceiptSha256": facts["semantic_receipt_sha256"]})
    return rows

def _refused_command(value: Any) -> str | None:
    if isinstance(value, dict):
        if value.get("type") in REFUSED_COMMANDS:
            return REFUSED_COMMANDS[value["type"]]
        return next((code for item in value.values() if (code := _refused_command(item))), None)
    if isinstance(value, list):
        return next((code for item in value if (code := _refused_command(item))), None)
    return None

def chapter_frame_violations(plan: dict[str, Any], frame_range: dict[str, int]) -> list[str]:
    """Every editorial frame (beat, graphic, transition, audio accent, colour exception) inside [start, end)."""
    start, end = frame_range["startFrame"], frame_range["endFrame"]
    editorial = require_mapping(plan.get("editorial"), "chapter plan editorial")
    issues: list[str] = []

    def span(label: str, value: Any) -> None:
        bounds = value if isinstance(value, dict) else {}
        low, high = bounds.get("startFrame"), bounds.get("endFrame")
        if type(low) is not int or type(high) is not int or not start <= low < high <= end:
            issues.append(label)

    def point(label: str, value: Any) -> None:
        if type(value) is not int or not start <= value < end:
            issues.append(label)

    narrative = require_mapping(editorial.get("narrative"), "chapter plan narrative")
    for index, beat in enumerate(require_list(narrative.get("beats"), "chapter plan beats")):
        beat = require_mapping(beat, "chapter beat")
        span(f"beat {beat.get('id', index)}", beat.get("range"))
    for index, graphic in enumerate(require_list(editorial.get("graphics", []), "chapter plan graphics")):
        graphic = require_mapping(graphic, "chapter graphic")
        span(f"graphic {graphic.get('id', index)}", graphic.get("range"))
    for index, transition in enumerate(require_list(editorial.get("transitions", []), "chapter plan transitions")):
        transition = require_mapping(transition, "chapter transition")
        point(f"transition {transition.get('id', index)}", transition.get("atFrame"))
    audio = require_mapping(editorial.get("audio", {}), "chapter plan audio")
    for field in ("impactFrames", "breathFrames"):
        for frame in require_list(audio.get(field, []), f"chapter plan {field}"):
            point(f"{field} {frame}", frame)
    color = require_mapping(editorial.get("color", {}), "chapter plan color")
    for index, exception in enumerate(require_list(color.get("exceptions", []), "chapter plan colour exceptions")):
        span(f"colour exception {index}", require_mapping(exception, "colour exception").get("range"))
    return issues
