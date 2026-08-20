# -*- coding: utf-8 -*-
"""Frozen same-input benchmark for professional editorial parity.

The harness separates candidate inputs from human references, hashes every
frozen artifact, and scores only blinded holdout ratings.  It intentionally
cannot manufacture a professional-parity claim from self-tests or templates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
SPLIT_TARGETS = {"calibration": 12, "regression": 6, "blind_holdout": 6}
SLOT_BLUEPRINTS = (
    ("S01", "calibration", "shorts", "travel", "hook-to-payoff continuity"),
    ("S02", "calibration", "shorts", "food", "appetite and proof"),
    ("S03", "calibration", "shorts", "beyblade", "battle state and finish"),
    ("S04", "regression", "shorts", "ai_teaching", "screen evidence and clarity"),
    ("S05", "blind_holdout", "shorts", "product", "feature to consequence"),
    ("S06", "blind_holdout", "shorts", "entertainment", "escalation and payoff"),
    ("L01", "calibration", "longform", "hook", "opening promise"),
    ("L02", "calibration", "longform", "explanation", "information hierarchy"),
    ("L03", "calibration", "longform", "proof", "claim and evidence"),
    ("L04", "regression", "longform", "escalation", "rising stakes"),
    ("L05", "regression", "longform", "breath", "intentional restraint"),
    ("L06", "blind_holdout", "longform", "payoff", "resolution and emotional hold"),
    ("V01", "calibration", "vfx", "fast_motion", "fast subject tracking"),
    ("V02", "calibration", "vfx", "occlusion", "foreground occlusion and roto"),
    ("V03", "calibration", "vfx", "similar_objects", "identity preservation"),
    ("V04", "regression", "vfx", "motion_blur", "blur and confidence loss"),
    ("V05", "regression", "vfx", "reflective_surface", "matte and light integration"),
    ("V06", "blind_holdout", "vfx", "camera_motion", "camera solve and composite"),
    ("N01", "calibration", "negative_control", "clean_cut", "effect should be rejected"),
    ("N02", "calibration", "negative_control", "clean_hold", "hold should remain quiet"),
    ("N03", "calibration", "negative_control", "room_tone", "audio should not be overfilled"),
    ("N04", "regression", "negative_control", "no_tracking", "static label beats fake tracking"),
    ("N05", "blind_holdout", "negative_control", "no_transition", "motivated hard cut"),
    ("N06", "blind_holdout", "negative_control", "no_template", "footage beats empty card"),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"benchmark path escapes dataset root: {relative}") from exc
    return path


def _file_record(root: Path, relative: str) -> dict[str, Any]:
    path = _inside(root, relative)
    if not path.is_file():
        raise ValueError(f"missing benchmark artifact: {relative}")
    return {"path": Path(relative).as_posix(), "bytes": path.stat().st_size,
            "sha256": _sha256(path)}


def _empty_slots() -> list[dict[str, Any]]:
    return [
        {"id": identifier, "split": split, "format": format_name,
         "domain": domain, "challenge": challenge, "source_files": [],
         "brief_file": None, "allowed_asset_manifest": None,
         "human_reference": None}
        for identifier, split, format_name, domain, challenge in SLOT_BLUEPRINTS
    ]


def init_dataset(dataset_dir: str | Path, contract_path: str | Path) -> dict[str, Any]:
    root = Path(dataset_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    contract = Path(contract_path).resolve()
    if not contract.is_file():
        raise ValueError(f"benchmark contract not found: {contract}")
    spec_path = root / "dataset_spec.json"
    if spec_path.exists():
        raise FileExistsError(f"refusing to overwrite existing spec: {spec_path}")
    for folder in ("inputs", "briefs", "assets", "references", "evaluations", "packets"):
        (root / folder).mkdir(exist_ok=True)
    spec = {
        "schema_version": SCHEMA_VERSION,
        "benchmark_id": "editorial-parity-v1",
        "contract": {"path": str(contract), "sha256": _sha256(contract)},
        "split_targets": SPLIT_TARGETS,
        "slots": _empty_slots(),
    }
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "UNBUILT", "dataset_dir": str(root), "spec": str(spec_path),
            "missing_slots": len(spec["slots"])}


def _freeze_slot(root: Path, slot: dict[str, Any]) -> dict[str, Any]:
    sources = slot.get("source_files") or []
    if not sources:
        raise ValueError(f"{slot.get('id')} has no source_files")
    required = ("brief_file", "allowed_asset_manifest", "human_reference")
    missing = [field for field in required if not slot.get(field)]
    if missing:
        raise ValueError(f"{slot.get('id')} missing {', '.join(missing)}")
    return {
        "id": slot["id"], "split": slot["split"], "format": slot["format"],
        "domain": slot["domain"], "challenge": slot["challenge"],
        "source_files": [_file_record(root, item) for item in sources],
        "brief_file": _file_record(root, slot["brief_file"]),
        "allowed_asset_manifest": _file_record(root, slot["allowed_asset_manifest"]),
        "human_reference": _file_record(root, slot["human_reference"]),
    }


def freeze_dataset(dataset_dir: str | Path, spec_path: str | Path | None = None) -> dict[str, Any]:
    root = Path(dataset_dir).resolve()
    spec_file = Path(spec_path).resolve() if spec_path else root / "dataset_spec.json"
    spec = _read_json(spec_file)
    expected_ids = {row[0] for row in SLOT_BLUEPRINTS}
    slots = spec.get("slots") or []
    if {row.get("id") for row in slots} != expected_ids or len(slots) != len(expected_ids):
        raise ValueError("dataset spec must contain the exact 24 benchmark slot ids")
    contract_path = Path((spec.get("contract") or {}).get("path", "")).resolve()
    if not contract_path.is_file():
        raise ValueError("dataset contract path is missing")
    contract_sha = _sha256(contract_path)
    if contract_sha != (spec.get("contract") or {}).get("sha256"):
        raise ValueError("benchmark contract drifted after dataset initialization")
    frozen = [_freeze_slot(root, row) for row in slots]
    manifest = {
        "schema_version": SCHEMA_VERSION, "benchmark_id": spec["benchmark_id"],
        "status": "FROZEN", "frozen_at": _now(),
        "contract": {"path": str(contract_path), "sha256": contract_sha},
        "spec_sha256": _sha256(spec_file), "split_targets": SPLIT_TARGETS,
        "slots": frozen,
    }
    manifest_path = root / "dataset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    result = validate_dataset(root)
    if result["status"] != "FROZEN_VALID":
        raise ValueError("frozen dataset failed validation: " + "; ".join(result["errors"]))
    return result


def validate_dataset(dataset_dir: str | Path) -> dict[str, Any]:
    root = Path(dataset_dir).resolve()
    manifest_path = root / "dataset_manifest.json"
    if not manifest_path.is_file():
        return {"status": "UNBUILT", "errors": ["dataset_manifest.json is missing"]}
    manifest = _read_json(manifest_path)
    errors: list[str] = []
    slots = manifest.get("slots") or []
    counts = Counter(row.get("split") for row in slots)
    if dict(counts) != SPLIT_TARGETS:
        errors.append(f"split counts drifted: {dict(counts)}")
    seen_by_split: dict[str, set[str]] = defaultdict(set)
    for slot in slots:
        for field in ("brief_file", "allowed_asset_manifest", "human_reference"):
            _verify_record(root, slot.get(field), f"{slot.get('id')}.{field}", errors)
        for record in slot.get("source_files") or []:
            if _verify_record(root, record, f"{slot.get('id')}.source", errors):
                seen_by_split[str(slot.get("split"))].add(record["sha256"])
    split_names = sorted(seen_by_split)
    for index, left in enumerate(split_names):
        for right in split_names[index + 1:]:
            overlap = seen_by_split[left] & seen_by_split[right]
            if overlap:
                errors.append(f"source leakage between {left} and {right}: {len(overlap)} hash(es)")
    contract = manifest.get("contract") or {}
    contract_path = Path(contract.get("path", ""))
    if not contract_path.is_file() or _sha256(contract_path) != contract.get("sha256"):
        errors.append("contract missing or hash drifted")
    return {"status": "FROZEN_VALID" if not errors else "BLOCKED",
            "errors": errors, "slot_count": len(slots), "split_counts": dict(counts),
            "manifest": str(manifest_path)}


def _verify_record(root: Path, record: Any, label: str, errors: list[str]) -> bool:
    if not isinstance(record, dict) or not record.get("path") or not record.get("sha256"):
        errors.append(f"{label} record is incomplete")
        return False
    try:
        path = _inside(root, record["path"])
    except ValueError as exc:
        errors.append(str(exc))
        return False
    if not path.is_file():
        errors.append(f"{label} file is missing")
        return False
    if path.stat().st_size != record.get("bytes") or _sha256(path) != record.get("sha256"):
        errors.append(f"{label} bytes/hash drifted")
        return False
    return True


def candidate_packet(dataset_dir: str | Path, project_id: str,
                     output: str | Path | None = None) -> dict[str, Any]:
    root = Path(dataset_dir).resolve()
    validation = validate_dataset(root)
    if validation["status"] != "FROZEN_VALID":
        raise ValueError("candidate packet requires a valid frozen dataset")
    manifest = _read_json(root / "dataset_manifest.json")
    slot = next((row for row in manifest["slots"] if row["id"] == project_id), None)
    if not slot:
        raise ValueError(f"unknown benchmark project: {project_id}")
    packet = {key: slot[key] for key in
              ("id", "split", "format", "domain", "challenge", "source_files",
               "brief_file", "allowed_asset_manifest")}
    packet["human_reference_exposed"] = False
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return packet


def score_holdout(dataset_dir: str | Path, contract_path: str | Path | None = None) -> dict[str, Any]:
    root = Path(dataset_dir).resolve()
    validation = validate_dataset(root)
    if validation["status"] != "FROZEN_VALID":
        return {"status": "BLOCKED", "reasons": validation["errors"]}
    manifest = _read_json(root / "dataset_manifest.json")
    contract_file = Path(contract_path).resolve() if contract_path else Path(manifest["contract"]["path"])
    contract = _read_json(contract_file)
    holdout = {row["id"]: row for row in manifest["slots"] if row["split"] == "blind_holdout"}
    ratings = [_read_json(path) for path in sorted((root / "evaluations").glob("*.json"))]
    reasons: list[str] = []
    accepted: list[dict[str, Any]] = []
    required_metrics = set(contract.get("required_metrics") or [])
    for rating in ratings:
        if rating.get("project_id") not in holdout:
            continue
        missing = required_metrics - set((rating.get("metrics") or {}).keys())
        if not rating.get("blinded") or rating.get("candidate_label") not in {"A", "B"}:
            reasons.append(f"{rating.get('project_id')} contains an unblinded rating")
        elif rating.get("choice") not in {"A", "B", "tie"}:
            reasons.append(f"{rating.get('project_id')} has an invalid blind choice")
        elif missing:
            reasons.append(f"{rating.get('project_id')} missing metrics: {sorted(missing)}")
        else:
            accepted.append(rating)
    minimum = int(contract.get("minimum_blind_ratings_per_project", 3))
    rating_counts = Counter(row["project_id"] for row in accepted)
    for project_id in holdout:
        if rating_counts[project_id] < minimum:
            reasons.append(f"{project_id} has {rating_counts[project_id]}/{minimum} blind ratings")
    metrics = _aggregate_ratings(accepted, holdout)
    gates = contract["promotion_thresholds"]
    if metrics["blind_pairwise_preference"] < float(gates["blind_pairwise_preference"]):
        reasons.append("blind pairwise preference is below threshold")
    low_domains = {key: value for key, value in metrics["domain_preference"].items()
                   if value < float(gates["minimum_domain_preference"])}
    if low_domains:
        reasons.append(f"domain preference below threshold: {low_domains}")
    if metrics["opening_promise_clarity"] < float(gates["opening_promise_clarity"]):
        reasons.append("opening promise clarity is below threshold")
    if metrics["effect_motivation_accuracy"] < float(gates["effect_motivation_accuracy"]):
        reasons.append("effect motivation accuracy is below threshold")
    if metrics["truth_and_provenance_compliance"] < float(gates["truth_and_provenance_compliance"]):
        reasons.append("truth/provenance compliance is below threshold")
    if metrics["critical_visual_regressions"] > int(gates["critical_visual_regressions"]):
        reasons.append("critical visual regressions exceed threshold")
    return {"status": "PROMOTED" if not reasons else "BLOCKED", "reasons": reasons,
            "accepted_ratings": len(accepted), "metrics": metrics}


def _aggregate_ratings(ratings: list[dict[str, Any]],
                       holdout: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not ratings:
        return {"blind_pairwise_preference": 0.0, "domain_preference": {},
                "opening_promise_clarity": 0.0, "effect_motivation_accuracy": 0.0,
                "truth_and_provenance_compliance": 0.0, "critical_visual_regressions": 0,
                "reported_metrics": {}}
    wins, domain_scores, domain_counts = 0.0, defaultdict(float), Counter()
    effect_correct = effect_total = 0
    reported: dict[str, list[float]] = defaultdict(list)
    for row in ratings:
        score = .5 if row["choice"] == "tie" else float(row["choice"] == row["candidate_label"])
        wins += score
        domain = holdout[row["project_id"]]["domain"]
        domain_scores[domain] += score
        domain_counts[domain] += 1
        effect_correct += int(row.get("effect_decisions_correct", 0))
        effect_total += int(row.get("effect_decisions_total", 0))
        for key, value in (row.get("metrics") or {}).items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                reported[key].append(float(value))
    return {
        "blind_pairwise_preference": round(wins / len(ratings), 4),
        "domain_preference": {key: round(domain_scores[key] / domain_counts[key], 4)
                              for key in sorted(domain_counts)},
        "opening_promise_clarity": round(sum(bool(row.get("premise_correct")) for row in ratings) /
                                           len(ratings), 4),
        "effect_motivation_accuracy": round(effect_correct / effect_total, 4) if effect_total else 1.0,
        "truth_and_provenance_compliance": round(
            sum(bool(row.get("truth_and_provenance_compliance")) for row in ratings) / len(ratings), 4),
        "critical_visual_regressions": sum(int(row.get("critical_visual_regressions", 0))
                                            for row in ratings),
        "reported_metrics": {key: round(sum(values) / len(values), 4)
                             for key, values in sorted(reported.items())},
    }


def selftest() -> None:
    with tempfile.TemporaryDirectory(prefix="editorial-parity-") as raw:
        root = Path(raw)
        contract = root / "contract.json"
        contract.write_text(json.dumps({"required_metrics": [], "minimum_blind_ratings_per_project": 1,
            "promotion_thresholds": {"blind_pairwise_preference": .45,
                "minimum_domain_preference": .35, "opening_promise_clarity": .85,
                "effect_motivation_accuracy": .9, "truth_and_provenance_compliance": 1,
                "critical_visual_regressions": 0}}), encoding="utf-8")
        initialized = init_dataset(root / "dataset", contract)
        assert initialized["status"] == "UNBUILT"
        assert validate_dataset(root / "dataset")["status"] == "UNBUILT"
        assert len(_empty_slots()) == 24 and Counter(row["split"] for row in _empty_slots()) == SPLIT_TARGETS
        escaped: list[str] = []
        assert not _verify_record(root / "dataset", {"path": "../escape", "sha256": "x"},
                                  "fixture", escaped)
        assert escaped and "escapes" in escaped[0]
    print("editorial_parity_benchmark selftest GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest")
    init = sub.add_parser("init")
    init.add_argument("dataset_dir")
    init.add_argument("--contract", required=True)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("dataset_dir")
    freeze.add_argument("--spec")
    validate = sub.add_parser("validate")
    validate.add_argument("dataset_dir")
    packet = sub.add_parser("packet")
    packet.add_argument("dataset_dir")
    packet.add_argument("project_id")
    packet.add_argument("--output")
    score = sub.add_parser("score")
    score.add_argument("dataset_dir")
    score.add_argument("--contract")
    args = parser.parse_args(argv)
    if args.command == "selftest":
        selftest()
        return 0
    if args.command == "init":
        result = init_dataset(args.dataset_dir, args.contract)
    elif args.command == "freeze":
        result = freeze_dataset(args.dataset_dir, args.spec)
    elif args.command == "validate":
        result = validate_dataset(args.dataset_dir)
    elif args.command == "packet":
        result = candidate_packet(args.dataset_dir, args.project_id, args.output)
    else:
        result = score_holdout(args.dataset_dir, args.contract)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"UNBUILT", "FROZEN_VALID", "PROMOTED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
