# -*- coding: utf-8 -*-
"""Hao aesthetic routing and human-review score contract.

The machine chooses a plausible style family and blocks known regressions.  It
does not pretend to judge taste: the ten visual dimensions require a human
rating and timestamped evidence before an edit can pass the aesthetic gate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_STANDARD = ROOT.parent / "knowledge" / "runtime" / "aesthetic_standard.json"


def load_standard(path: str | Path = DEFAULT_STANDARD) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_standard(standard: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    dimensions = standard.get("dimensions") or {}
    if sum(float(row.get("weight", 0)) for row in dimensions.values()) != 100:
        errors.append("aesthetic dimension weights must sum to 100")
    families = standard.get("style_families") or {}
    if not families:
        errors.append("style families are required")
    for domain, route in (standard.get("domain_routes") or {}).items():
        keys = [route.get("primary"), *(route.get("support") or [])]
        unknown = [key for key in keys if key not in families]
        if unknown:
            errors.append("%s route has unknown families: %s" % (domain, unknown))
    contract = standard.get("score_contract") or {}
    if float(contract.get("pass_score", 0)) <= float(contract.get("block_below", 0)):
        errors.append("pass_score must be above block_below")
    benchmark_dims = {"mrbeast_information_energy", "yingshi_hurricane_cinematic_craft"}
    for format_key in ("shorts", "longform"):
        multipliers = (standard.get("format_multipliers") or {}).get(format_key) or {}
        missing = sorted(key for key in benchmark_dims if float(multipliers.get(key, 0)) <= 0)
        if missing:
            errors.append(f"{format_key} must score both formal benchmarks: {missing}")
    return errors


def _format_key(value: str) -> str:
    key = str(value or "shorts").lower()
    if key in {"short", "shorts", "reel", "reels", "portrait"}:
        return "shorts"
    if key in {"long", "longform", "youtube", "landscape"}:
        return "longform"
    raise ValueError("unknown format %r" % value)


def resolve_style_route(domain: str, format: str = "shorts",
                        standard: dict[str, Any] | None = None) -> dict[str, Any]:
    standard = standard or load_standard()
    domain_key = str(domain or "general").lower()
    route = (standard.get("domain_routes") or {}).get(domain_key)
    if not route:
        domain_key, route = "general", standard["domain_routes"]["general"]
    family = standard["style_families"][route["primary"]]
    support = [standard["style_families"][key] for key in route.get("support", [])]
    format_key = _format_key(format)
    return {
        "standard_id": standard["standard_id"],
        "standard_version": standard["version"],
        "domain": domain_key,
        "format": format_key,
        "primary_family": route["primary"],
        "primary_label": family["label_zh"],
        "primary_template": family["templates"][0],
        "allowed_templates": list(dict.fromkeys(
            family["templates"] + [template for row in support for template in row["templates"]]
        )),
        "support_families": list(route.get("support", [])),
        "avoid": list(route.get("avoid", [])),
        "format_rule": standard["format_rules"][format_key],
        "shared_dna": standard["reference_basis"]["shared_dna"],
        "formal_benchmarks": ["mrbeast_information_energy", "yingshi_hurricane_cinematic_craft"],
    }


def review_schema(format: str = "shorts",
                  standard: dict[str, Any] | None = None) -> dict[str, Any]:
    standard = standard or load_standard()
    format_key = _format_key(format)
    multipliers = standard["format_multipliers"][format_key]
    weighted = {
        key: float(row["weight"]) * float(multipliers.get(key, 1))
        for key, row in standard["dimensions"].items()
    }
    total = sum(weighted.values()) or 1
    return {
        "format": format_key,
        "dimensions": {
            key: {
                "label_zh": row["label_zh"],
                "question": row["question"],
                "weight": round(weighted[key] * 100 / total, 3),
            }
            for key, row in standard["dimensions"].items()
        },
        "contract": standard["score_contract"],
    }


def _signal_blockers(signals: dict[str, Any]) -> list[str]:
    blockers = []
    truthy = {
        "generic_fullscreen_card", "grid_used_as_default_opener",
        "template_role_label_visible", "unmotivated_geometric_transition",
        "exact_reference_layout_copy", "visual_density_overload",
    }
    blockers.extend(sorted(key for key in truthy if signals.get(key) is True))
    for key in ("text_safe_area_pass", "style_domain_match"):
        if signals.get(key) is False:
            blockers.append(key + "=false")
    return blockers


def score_review(review: dict[str, Any], *, format: str = "shorts",
                 signals: dict[str, Any] | None = None,
                 standard: dict[str, Any] | None = None) -> dict[str, Any]:
    standard = standard or load_standard()
    schema = review_schema(format, standard)
    ratings = review.get("ratings") or {}
    rows, earned, missing = [], 0.0, []
    low = []
    minimum = float(schema["contract"]["minimum_dimension_rating"])
    for key, dim in schema["dimensions"].items():
        raw = ratings.get(key)
        if raw is None:
            missing.append(key)
            rating = 0.0
        else:
            rating = max(1.0, min(5.0, float(raw)))
        points = rating / 5.0 * float(dim["weight"])
        earned += points
        if raw is not None and rating < minimum:
            low.append(key)
        rows.append({"id": key, "label_zh": dim["label_zh"], "rating": rating,
                     "weight": dim["weight"], "points": round(points, 2),
                     "question": dim["question"]})
    score = round(earned, 1)
    blockers = _signal_blockers(signals or {})
    completed = not missing and bool(review.get("completed_at") or review.get("review_id"))
    contract = schema["contract"]
    if blockers or (completed and score < float(contract["block_below"])):
        status = "BLOCKED"
    elif completed and not low and score >= float(contract["pass_score"]):
        status = "PASSED"
    else:
        status = "REVIEW"
    return {
        "schema_version": 1,
        "standard_id": standard["standard_id"],
        "standard_version": standard["version"],
        "status": status,
        "score": score,
        "target": float(contract["pass_score"]),
        "completed": completed,
        "missing_dimensions": missing,
        "low_dimensions": low,
        "blockers": blockers,
        "dimensions": rows,
        "rule": "human score >= target + every dimension >= minimum + no machine blocker",
    }


def compact_review_dimensions(format: str = "shorts") -> dict[str, str]:
    schema = review_schema(format)
    return {key: row["label_zh"] for key, row in schema["dimensions"].items()}


def self_test() -> None:
    standard = load_standard()
    assert not validate_standard(standard)
    ai = resolve_style_route("ai", "shorts", standard)
    assert ai["primary_template"] == "cyan_lab"
    assert "ai_chalk_grid" not in ai["allowed_templates"]
    toy = resolve_style_route("toy", "shorts", standard)
    assert toy["primary_family"] == "shape_play"
    for format_key in ("shorts", "longform"):
        dims_for_format = review_schema(format_key, standard)["dimensions"]
        assert "mrbeast_information_energy" in dims_for_format
        assert "yingshi_hurricane_cinematic_craft" in dims_for_format
    dims = list(standard["dimensions"])
    clean = {"ratings": {key: 4.5 for key in dims}, "completed_at": "2026-08-11T00:00:00Z"}
    assert score_review(clean, signals={"text_safe_area_pass": True})["status"] == "PASSED"
    pending = {"ratings": {key: 5 for key in dims[:-1]}}
    assert score_review(pending)["status"] == "REVIEW"
    bad = {"ratings": {key: 5 for key in dims}, "completed_at": "now"}
    assert score_review(bad, signals={"grid_used_as_default_opener": True})["status"] == "BLOCKED"
    mismatch = score_review(bad, signals={"style_domain_match": False})
    assert mismatch["status"] == "BLOCKED"
    print("aesthetic score self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest")
    route = sub.add_parser("route")
    route.add_argument("--domain", default="general")
    route.add_argument("--format", default="shorts")
    score = sub.add_parser("score")
    score.add_argument("review")
    score.add_argument("--format", default="shorts")
    args = parser.parse_args(argv)
    if args.command == "selftest":
        self_test()
        return 0
    if args.command == "route":
        print(json.dumps(resolve_style_route(args.domain, args.format), ensure_ascii=False, indent=2))
        return 0
    review = json.loads(Path(args.review).read_text(encoding="utf-8"))
    report = score_review(review, format=args.format, signals=review.get("signals") or {})
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
