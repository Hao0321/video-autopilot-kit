# -*- coding: utf-8 -*-
"""Validate and query the evidence-backed MrBeast production source map."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


def _default_map_path() -> Path:
    canonical = ROOT / "knowledge" / "mrbeast_effect_source_map.json"
    public = ROOT.parent / "knowledge" / "runtime" / "mrbeast_effect_source_map.json"
    return canonical if canonical.is_file() else public


MAP_PATH = _default_map_path()
CAPABILITIES = {
    "VERIFIED_AUTO",
    "AUTO_WITH_REVIEW",
    "VERIFIED_MANUAL",
    "IMPLEMENTED_UNVERIFIED",
    "SHOT_SPECIFIC_MANUAL",
    "EXTERNAL_3D_VFX",
}
VALID_TIERS = {"A", "B", "C"}


def load_map(path: Path = MAP_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_map(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    source_ids = {row.get("id") for row in data.get("research_method", {}).get("sources", [])}
    seen: set[str] = set()
    for row in data.get("effects", []):
        effect_id = str(row.get("id", ""))
        if not effect_id:
            errors.append("effect missing id")
        elif effect_id in seen:
            errors.append("duplicate effect id: " + effect_id)
        seen.add(effect_id)
        if row.get("capability") not in CAPABILITIES:
            errors.append(f"{effect_id}: invalid capability")
        if not row.get("function"):
            errors.append(f"{effect_id}: missing function")
        if not row.get("qa"):
            errors.append(f"{effect_id}: missing QA")
        if row.get("not_an_asset") and row.get("asset_jobs"):
            errors.append(f"{effect_id}: not_an_asset cannot emit asset jobs")
        for evidence in row.get("source_evidence", []):
            if ":" not in evidence:
                errors.append(f"{effect_id}: malformed evidence {evidence}")
                continue
            source, tier = evidence.rsplit(":", 1)
            if source not in source_ids:
                errors.append(f"{effect_id}: unknown source {source}")
            if tier not in VALID_TIERS:
                errors.append(f"{effect_id}: invalid evidence tier {tier}")
    if not data.get("global_blockers"):
        errors.append("global blockers missing")
    return errors


def asset_backlog(data: dict[str, Any]) -> list[dict[str, Any]]:
    jobs: dict[str, dict[str, Any]] = {}
    for effect in data.get("effects", []):
        for job_id in effect.get("asset_jobs", []):
            jobs.setdefault(job_id, {
                "id": job_id,
                "source_effects": [],
                "department": effect.get("department"),
                "capability": effect.get("capability"),
                "status": "SPECIFIED_NOT_BUILT",
                "human_motion_review_required": True,
            })
            jobs[job_id]["source_effects"].append(effect.get("id"))
    return sorted(jobs.values(), key=lambda row: row["id"])


def summary(data: dict[str, Any]) -> dict[str, Any]:
    effects = data.get("effects", [])
    capabilities = Counter(row.get("capability") for row in effects)
    departments = Counter(row.get("department") for row in effects)
    return {
        "schema_version": data.get("schema_version"),
        "version": data.get("version"),
        "effect_count": len(effects),
        "asset_job_count": len(asset_backlog(data)),
        "capabilities": dict(sorted(capabilities.items())),
        "departments": dict(sorted(departments.items())),
        "errors": validate_map(data),
    }


def self_test() -> None:
    data = load_map()
    assert not validate_map(data), validate_map(data)
    backlog = asset_backlog(data)
    assert any(row["id"] == "type_rig_white_depth_v1" for row in backlog)
    assert any(row["id"] == "camera_solve_handoff_v1" for row in backlog)
    editorial = next(row for row in data["effects"] if row["id"] == "editorial_clarity_scale_payoff")
    assert editorial["not_an_asset"] and not editorial.get("asset_jobs")
    print("mrbeast_source_map self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect the MrBeast production source map")
    parser.add_argument("command", choices=["audit", "backlog", "selftest"])
    args = parser.parse_args(argv)
    if args.command == "selftest":
        self_test()
        return 0
    data = load_map()
    output: Any = summary(data) if args.command == "audit" else asset_backlog(data)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 1 if args.command == "audit" and output["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
