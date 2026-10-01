# -*- coding: utf-8 -*-
"""Validate and query the evidence-backed MrBeast production source map."""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[2]
EVIDENCE_ROOT = ROOT / "knowledge" / "effect_evidence"


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
MIN_REPRESENTATIVE_SHOTS = 3
MIN_REPRESENTATIVE_DOMAINS = 2
AUTO_PROMOTION_CANDIDATES = {"IMPLEMENTED_UNVERIFIED", "AUTO_WITH_REVIEW"}


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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_evidence_artifact(project_root: Path, raw_path: Any) -> Path | None:
    value = str(raw_path or "").replace("\\", "/")
    relative = Path(value)
    if not value or relative.is_absolute() or ".." in relative.parts:
        return None
    target = (project_root / relative).resolve()
    try:
        target.relative_to(project_root.resolve())
    except ValueError:
        return None
    return target


def _assertion_passes(assertion: dict[str, Any]) -> bool:
    try:
        value = float(assertion["value"])
        threshold = float(assertion["threshold"])
    except (KeyError, TypeError, ValueError):
        return False
    result = {
        "<=": value <= threshold,
        "<": value < threshold,
        ">=": value >= threshold,
        ">": value > threshold,
        "==": value == threshold,
    }.get(assertion.get("operator"), False)
    return bool(result and assertion.get("pass") is True and assertion.get("metric"))


def validate_effect_evidence(record: dict[str, Any], effect_id: str,
                             project_root: Path = PROJECT_ROOT) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if record.get("effect_id") != effect_id:
        errors.append("effect_id does not match evidence filename")
    shots = record.get("representative_shots") or []
    if len(shots) < MIN_REPRESENTATIVE_SHOTS:
        errors.append(f"requires at least {MIN_REPRESENTATIVE_SHOTS} representative shots")
    domains = {row.get("domain") for row in shots if row.get("domain")}
    if len(domains) < MIN_REPRESENTATIVE_DOMAINS:
        errors.append(f"requires at least {MIN_REPRESENTATIVE_DOMAINS} representative domains")
    for index, shot in enumerate(shots):
        prefix = f"shot[{index}]"
        if not shot.get("shot_id"):
            errors.append(f"{prefix}.shot_id is required")
        if not shot.get("domain"):
            errors.append(f"{prefix}.domain is required")
        try:
            source_in = float(shot.get("source_in"))
            source_out = float(shot.get("source_out"))
            if source_in < 0 or source_out <= source_in:
                errors.append(f"{prefix} source range is invalid")
        except (TypeError, ValueError):
            errors.append(f"{prefix} source_in/source_out must be numeric")
        artifacts = (
            ("source_path", "source_sha256"),
            ("render_path", "render_sha256"),
            ("frame_qa_path", "frame_qa_sha256"),
            ("review_path", "review_sha256"),
        )
        for path_field, hash_field in artifacts:
            value = str(shot.get(hash_field, ""))
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
                errors.append(f"{prefix}.{hash_field} must be a SHA-256")
                continue
            artifact = _resolve_evidence_artifact(project_root, shot.get(path_field))
            if artifact is None:
                errors.append(f"{prefix}.{path_field} must be a safe repo-relative path")
            elif not artifact.is_file():
                errors.append(f"{prefix}.{path_field} does not exist")
            elif _sha256_file(artifact) != value.lower():
                errors.append(f"{prefix}.{hash_field} does not match {path_field}")
        assertions = shot.get("technical_assertions") or []
        if not assertions:
            errors.append(f"{prefix}.technical_assertions are required")
        for assertion_index, assertion in enumerate(assertions):
            if not isinstance(assertion, dict) or not _assertion_passes(assertion):
                errors.append(
                    f"{prefix}.technical_assertions[{assertion_index}] is not a passing measured assertion"
                )
        if shot.get("technical_qa") != "PASS":
            errors.append(f"{prefix}.technical_qa must be PASS")
        if shot.get("hao_review") != "APPROVED":
            errors.append(f"{prefix}.hao_review must be APPROVED")
        if not shot.get("real_footage"):
            errors.append(f"{prefix} must use real footage")
    if record.get("promotion_decision") != "VERIFIED_AUTO":
        errors.append("promotion_decision must be VERIFIED_AUTO")
    return errors


def effect_evidence_audit(data: dict[str, Any],
                          evidence_root: Path = EVIDENCE_ROOT) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    verified = 0
    eligible = 0
    for effect in data.get("effects", []):
        effect_id = effect["id"]
        capability = effect.get("capability")
        if capability not in AUTO_PROMOTION_CANDIDATES:
            rows.append({"effect_id": effect_id, "declared_capability": capability,
                         "evidence_status": "NOT_AUTO_PROMOTION_SCOPE", "evidence": None,
                         "errors": []})
            continue
        eligible += 1
        evidence_path = evidence_root / f"{effect_id}.json"
        if evidence_path.is_file():
            try:
                record = json.loads(evidence_path.read_text(encoding="utf-8"))
                errors = validate_effect_evidence(record, effect_id)
            except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
                errors = [f"invalid evidence JSON: {exc}"]
        else:
            errors = ["representative real-footage evidence is missing"]
        status = "VERIFIED_AUTO" if not errors else "UNVERIFIED"
        verified += int(status == "VERIFIED_AUTO")
        rows.append({"effect_id": effect_id, "declared_capability": capability,
                     "evidence_status": status, "evidence": str(evidence_path),
                     "errors": errors})
    return {"status": "GREEN", "effect_count": len(rows),
            "auto_promotion_candidates": eligible, "verified_auto": verified,
            "unverified_auto_candidates": eligible - verified,
            "not_auto_promotion_scope": len(rows) - eligible, "effects": rows,
            "promotion_rule": "3 real-footage shots, 2 domains, hash-verified artifacts, measured technical QA and Hao approval"}


def self_test() -> None:
    data = load_map()
    assert not validate_map(data), validate_map(data)
    backlog = asset_backlog(data)
    assert any(row["id"] == "type_rig_white_depth_v1" for row in backlog)
    assert any(row["id"] == "camera_solve_handoff_v1" for row in backlog)
    editorial = next(row for row in data["effects"] if row["id"] == "editorial_clarity_scale_payoff")
    assert editorial["not_an_asset"] and not editorial.get("asset_jobs")
    with tempfile.TemporaryDirectory(prefix="effect-evidence-") as raw:
        project_root = Path(raw)
        artifact = project_root / "evidence.bin"
        artifact.write_bytes(b"real evidence fixture")
        digest = _sha256_file(artifact)
        shot = {"shot_id": "fixture-1", "domain": "toy", "source_in": 0,
                "source_out": 1, "source_path": "evidence.bin", "source_sha256": digest,
                "render_path": "evidence.bin", "render_sha256": digest,
                "frame_qa_path": "evidence.bin", "frame_qa_sha256": digest,
                "review_path": "evidence.bin", "review_sha256": digest,
                "technical_assertions": [{"metric": "drift_px_p95", "operator": "<=",
                                           "value": 2.0, "threshold": 3.0, "pass": True}],
                "technical_qa": "PASS", "hao_review": "APPROVED", "real_footage": True}
        valid = {"schema_version": 1, "effect_id": "fixture",
                 "promotion_decision": "VERIFIED_AUTO", "representative_shots": [
                     dict(shot), {**shot, "shot_id": "fixture-2", "domain": "travel"},
                     {**shot, "shot_id": "fixture-3"},
                 ]}
        assert not validate_effect_evidence(valid, "fixture", project_root)
        valid["representative_shots"][0]["hao_review"] = "PENDING"
        assert validate_effect_evidence(valid, "fixture", project_root)
    print("mrbeast_source_map self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect the MrBeast production source map")
    parser.add_argument("command", choices=["audit", "backlog", "evidence", "selftest"])
    args = parser.parse_args(argv)
    if args.command == "selftest":
        self_test()
        return 0
    data = load_map()
    if args.command == "audit":
        output: Any = summary(data)
    elif args.command == "evidence":
        output = effect_evidence_audit(data)
    else:
        output = asset_backlog(data)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 1 if args.command == "audit" and output["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
