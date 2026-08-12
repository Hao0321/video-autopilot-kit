# -*- coding: utf-8 -*-
"""Explainable pre-publish score for YouTube title/thumbnail packaging.

This is deliberately not a CTR predictor.  It combines explicit human ratings
with objective image facts, reports risks, and leaves the final winner to
YouTube Test & Compare and post-publish retention/satisfaction evidence.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
DEFAULT_STANDARD = HERE.parent / "knowledge" / "runtime" / "thumbnail_algorithm_standard.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".thumbnail-score-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def load_standard(path: str | Path = DEFAULT_STANDARD) -> dict[str, Any]:
    return _read_json(Path(path))


def validate_standard(standard: dict[str, Any]) -> list[str]:
    errors = []
    dimensions = standard.get("dimensions") or {}
    if round(sum(float(row.get("weight", 0)) for row in dimensions.values()), 6) != 100:
        errors.append("thumbnail dimension weights must sum to 100")
    if float(standard.get("ready_score", 0)) <= float(standard.get("block_below", 0)):
        errors.append("ready_score must be above block_below")
    if not 0 < float(standard.get("minimum_critical_value", 0)) <= 1:
        errors.append("minimum_critical_value must be within 0..1")
    return errors


def analyze_image(path: str | Path, *, preview_dir: str | Path | None = None) -> dict[str, Any]:
    """Read objective image facts and optionally render a 168x94 mobile preview."""
    from PIL import Image, ImageStat

    source = Path(path).expanduser().resolve()
    with Image.open(source) as opened:
        image = opened.convert("RGB")
        width, height = image.size
        grayscale = image.convert("L")
        stats = ImageStat.Stat(grayscale)
        contrast_stddev = round(float(stats.stddev[0]), 2)
        ratio = width / height if height else 0.0
        preview_path = None
        if preview_dir is not None:
            preview_path = Path(preview_dir) / "THUMBNAIL_MOBILE_168.jpg"
            preview_path.parent.mkdir(parents=True, exist_ok=True)
            preview = image.resize((168, 94), Image.Resampling.LANCZOS)
            preview.save(preview_path, quality=92, optimize=True)
    return {
        "path": str(source),
        "width": width,
        "height": height,
        "aspect_ratio": round(ratio, 4),
        "aspect_16_9": abs(ratio - (16 / 9)) <= 0.03,
        "resolution_pass": width >= 1280 and height >= 720,
        "luma_contrast_stddev": contrast_stddev,
        "mobile_preview": str(preview_path.resolve()) if preview_path else None,
    }


def _value(raw: Any) -> tuple[float, str]:
    if isinstance(raw, dict):
        value = raw.get("value")
        proof = str(raw.get("evidence", ""))
    else:
        value, proof = raw, "numeric evidence"
    try:
        return max(0.0, min(1.0, float(value))), proof
    except (TypeError, ValueError):
        return 0.0, "missing"


def _signal_hits(signals: dict[str, Any], standard: dict[str, Any]) -> list[dict[str, Any]]:
    hits = []
    for rule in standard.get("negative_signals", []):
        expected = rule.get("when") or {}
        if expected and all(signals.get(key) == value for key, value in expected.items()):
            hits.append({key: rule[key] for key in ("id", "severity", "message")})
    return hits


def score_thumbnail(evidence: dict[str, Any],
                    standard: dict[str, Any] | None = None) -> dict[str, Any]:
    standard = standard or load_standard()
    errors = validate_standard(standard)
    if errors:
        raise ValueError("; ".join(errors))
    provided = evidence.get("dimensions") or {}
    rows, missing, low_critical, earned = [], [], [], 0.0
    minimum = float(standard["minimum_critical_value"])
    for name, definition in standard["dimensions"].items():
        if name not in provided:
            missing.append(name)
        value, proof = _value(provided.get(name))
        weight = float(definition["weight"])
        points = value * weight
        earned += points
        if definition.get("critical") and value < minimum:
            low_critical.append(name)
        rows.append({
            "id": name,
            "label_zh": definition["label_zh"],
            "weight": weight,
            "value": round(value, 3),
            "points": round(points, 2),
            "evidence": proof,
        })
    score = round(earned, 1)
    signals = dict(evidence.get("signals") or {})
    image_metrics = dict(evidence.get("image_metrics") or {})
    if "aspect_16_9" in image_metrics:
        signals["aspect_16_9"] = bool(image_metrics["aspect_16_9"])
    hits = _signal_hits(signals, standard)
    blocks = [row for row in hits if row["severity"] == "BLOCK"]
    reviews = [row for row in hits if row["severity"] == "REVIEW"]
    completed = not missing
    if not completed:
        status = "REVIEW"
    elif blocks or score < float(standard["block_below"]):
        status = "BLOCKED"
    elif (score >= float(standard["ready_score"]) and not low_critical and not reviews):
        status = "PACKAGING_READY"
    else:
        status = "REVISE"
    weak = sorted(rows, key=lambda row: row["points"] / row["weight"] if row["weight"] else 0)
    recommendations = []
    for row in weak[:3]:
        if row["value"] < 0.85:
            recommendations.append(standard["dimensions"][row["id"]]["improvement"])
    recommendations.extend(row["message"] for row in reviews)
    return {
        "schema_version": 1,
        "standard_id": standard["standard_id"],
        "status": status,
        "score": score,
        "target": float(standard["ready_score"]),
        "completed": completed,
        "missing_dimensions": missing,
        "low_critical_dimensions": low_critical,
        "dimensions": rows,
        "negative_signals": hits,
        "recommendations": list(dict.fromkeys(recommendations)),
        "image_metrics": image_metrics,
        "rule": "score>=85 + critical dimensions>=0.65 + no BLOCK/REVIEW signal",
        "disclaimer": standard["disclaimer"],
    }


def write_report(output_dir: str | Path, evidence: dict[str, Any]) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    report = score_thumbnail(evidence)
    report["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    json_path = output / "THUMBNAIL_SCORE.json"
    _atomic_json(json_path, {**report, "evidence": evidence})
    lines = [
        "# 封面演算法預發布評分", "",
        f"- 狀態：**{report['status']}**",
        f"- 分數：**{report['score']} / 100**（ready 門檻 {report['target']}）",
        f"- 封面：`{evidence.get('image', '未指定')}`", "",
        "## 維度", "",
    ]
    lines.extend(
        "- %s：%.1f / %.0f — %s" %
        (row["label_zh"], row["points"], row["weight"], row["evidence"])
        for row in report["dimensions"]
    )
    if report["negative_signals"]:
        lines += ["", "## 風險命中", ""] + [
            "- [%s] %s：%s" % (row["severity"], row["id"], row["message"])
            for row in report["negative_signals"]
        ]
    if report["recommendations"]:
        lines += ["", "## 下一版先改", ""] + [
            f"- {item}" for item in report["recommendations"]
        ]
    lines += ["", f"> {report['disclaimer']}", ""]
    markdown_path = output / "THUMBNAIL_SCORE.md"
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    report["json"] = str(json_path.resolve())
    report["markdown"] = str(markdown_path.resolve())
    return report


def self_test() -> None:
    standard = load_standard()
    assert not validate_standard(standard)
    clean = {
        "dimensions": {name: 1.0 for name in standard["dimensions"]},
        "signals": {"aspect_16_9": True},
    }
    assert score_thumbnail(clean)["status"] == "PACKAGING_READY"
    pending = {"dimensions": {"click_promise_clarity": 1.0}}
    assert score_thumbnail(pending)["status"] == "REVIEW"
    misleading = json.loads(json.dumps(clean))
    misleading["signals"]["unsafe_or_misleading_claim"] = True
    assert score_thumbnail(misleading)["status"] == "BLOCKED"
    revise = json.loads(json.dumps(clean))
    revise["dimensions"]["promise_payoff_alignment"] = 0.5
    assert score_thumbnail(revise)["status"] == "REVISE"
    print("thumbnail algorithm score self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest")
    score = sub.add_parser("score")
    score.add_argument("evidence")
    score.add_argument("--image", default="")
    score.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    if args.command == "selftest":
        self_test()
        return 0
    evidence_path = Path(args.evidence).expanduser().resolve()
    evidence = _read_json(evidence_path)
    image_value = args.image or evidence.get("image", "")
    if image_value:
        image_path = Path(str(image_value)).expanduser()
        if not image_path.is_absolute():
            image_path = evidence_path.parent / image_path
        evidence["image"] = str(image_path.resolve())
        evidence["image_metrics"] = analyze_image(image_path, preview_dir=args.output_dir)
    report = write_report(args.output_dir, evidence)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
