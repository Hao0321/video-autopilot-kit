# -*- coding: utf-8 -*-
"""Quality-95 certification layer for short and long video delivery.

Mechanical checks can reject known failures.  Only a timestamped human review
can certify taste.  Reports therefore separate provisional machine confidence
from the final 95/100 certification instead of pretending green tests equal art.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from asset_memory import asset_fatigue_report
from aesthetic_score import score_review as score_aesthetic_review
from project_paths import discover_project_root
from quality_corpus import detect_negative, load_corpus, narrative_similarity


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = discover_project_root(ROOT)
NARRATIVE_STATE = PROJECT_ROOT / "videos" / "_state" / "quality_narratives.json"


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".quality-95-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def narrative_report(content_id: str, signature: str,
                     state_path: str | Path = NARRATIVE_STATE) -> dict:
    state = _read_json(Path(state_path), {"items": []})
    candidates = [row for row in state.get("items", []) if row.get("content_id") != content_id]
    ranked = sorted((
        {"content_id": row.get("content_id"),
         "similarity": round(narrative_similarity(signature, row.get("signature", "")), 3)}
        for row in candidates
    ), key=lambda row: -row["similarity"])
    peak = ranked[0]["similarity"] if ranked else 0.0
    return {"peak_similarity": peak, "high": peak >= .72, "nearest": ranked[:3]}


def record_narrative(content_id: str, signature: str,
                     state_path: str | Path = NARRATIVE_STATE) -> None:
    path = Path(state_path)
    state = _read_json(path, {"schema_version": 1, "items": []})
    items = [row for row in state.get("items", []) if row.get("content_id") != content_id]
    items.append({"content_id": content_id, "signature": str(signature)[:1200],
                  "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    state["items"] = items[-200:]
    _atomic_json(path, state)


def _value(evidence: dict, name: str) -> tuple[float, str]:
    raw = evidence.get("dimensions", {}).get(name)
    if isinstance(raw, dict):
        return max(0.0, min(1.0, float(raw.get("value", 0)))), str(raw.get("evidence", ""))
    if isinstance(raw, bool):
        return (1.0 if raw else 0.0), "boolean evidence"
    if isinstance(raw, (int, float)):
        return max(0.0, min(1.0, float(raw))), "numeric evidence"
    return 0.0, "missing"


def score_quality(evidence: dict[str, Any], corpus: dict[str, Any] | None = None) -> dict:
    corpus = corpus or load_corpus()
    dimensions, rows = corpus["dimensions"], []
    earned = 0.0
    for name, weight in dimensions.items():
        value, proof = _value(evidence, name)
        points = value * float(weight)
        earned += points
        rows.append({"id": name, "weight": weight, "value": round(value, 3),
                     "points": round(points, 2), "evidence": proof})
    score = round(earned, 1)
    signals = dict(evidence.get("signals") or {})
    hits = detect_negative(signals, corpus)
    blocks = [row for row in hits if row["severity"] == "BLOCK"]
    reviews = [row for row in hits if row["severity"] == "REVIEW"]
    human_value, _ = _value(evidence, "human_aesthetic_review")
    human_complete = bool(evidence.get("human_review", {}).get("completed")) and human_value > 0
    aesthetic = dict(evidence.get("aesthetic_review") or {})
    aesthetic_status = aesthetic.get("status", "REVIEW")
    if aesthetic_status == "BLOCKED":
        aesthetic_hit = {"id": "aesthetic-review-blocked", "severity": "BLOCK",
                         "message": "Hao aesthetic review contains a blocker or scores below 70."}
        blocks.append(aesthetic_hit)
        hits.append(aesthetic_hit)
    if blocks or score < 85:
        status = "BLOCKED"
    elif (score >= float(corpus.get("target_score", 95)) and human_complete and
          aesthetic_status == "PASSED" and not reviews):
        status = "CERTIFIED_95"
    else:
        status = "REVIEW"
    return {
        "schema_version": 1,
        "status": status,
        "score": score,
        "target": float(corpus.get("target_score", 95)),
        "human_review_complete": human_complete,
        "aesthetic_review_status": aesthetic_status,
        "aesthetic_review": aesthetic,
        "dimensions": rows,
        "negative_regressions": hits,
        "certification_rule": "score>=95 + Hao aesthetic PASSED + human review complete + no BLOCK/REVIEW regression",
    }


def short_evidence(*, content_id: str, spec: dict, ready: dict, qa: dict,
                   visual_plan: dict, tracked_report: dict | None = None,
                   project_root: str | Path = PROJECT_ROOT) -> dict:
    """Adapt a rendered Short into the shared Quality-95 evidence contract."""
    caption_text = " ".join(
        "".join(str(text) for text, _color in blocks)
        for _start, _end, blocks, kind in ready.get("caps", []) if kind != "addr"
    )
    signature = " ".join((str(spec.get("name", "")), str(spec.get("what", "")), caption_text))
    narrative = narrative_report(content_id, signature)
    selected = (visual_plan.get("asset_intelligence") or {}).get("selected_bgm_asset_id")
    fatigue = asset_fatigue_report([selected] if selected else [], project_root)
    sequences = visual_plan.get("sequence_plan") or []
    transitions_ok = all(row.get("cut_motivation") in {
        "action_or_information_change", "hold_for_contrast", "matched_motion",
        "occlusion", "spatial_continuity"
    } for row in sequences)
    tracking_config = spec.get("tracked_graphics") or {}
    tracked_labels = tracking_config.get("tracked_labels", [])
    lock_effects = tracking_config.get("lock_effects", [])
    mask_sheens = tracking_config.get("mask_sheens", [])
    tracking_present = bool(tracked_labels or lock_effects or mask_sheens)
    tracking_required = bool(spec.get("tracking_required", False) or spec.get("battle_matchup"))
    tracking_report_green = bool(tracked_report and tracked_report.get("status") == "GREEN")
    tracking_evidence = all(
        row.get("evidence") for row in tracked_labels + lock_effects + mask_sheens
    )
    tracking_ok = ((not tracking_required and not tracking_present) or
                   (tracking_present and tracking_report_green and tracking_evidence))
    persistent = str(spec.get("persistent_label_policy", "required")) != "omit"
    has_location = bool(spec.get("place") and spec.get("addr") and persistent)
    signals = {
        "generic_fullscreen_card": False,
        "grid_used_as_default_opener": False,
        "template_role_label_visible": False,
        "unmotivated_geometric_transition": False,
        "text_safe_area_pass": bool(qa.get("caption_sheet") and qa.get("first_frame")),
        "persistent_location_strip": persistent,
        "content_has_location_value": has_location,
        "tracked_label_present": tracking_present,
        "tracked_label_has_evidence": tracking_evidence if tracking_present else not tracking_required,
        "tracking_required_by_route": tracking_required,
        "narrative_similarity_high": narrative["high"],
        "asset_fatigue_high": fatigue["status"] == "REVIEW",
        "style_domain_match": True,
        "exact_reference_layout_copy": False,
        "visual_density_overload": False,
    }
    signals.update(dict(spec.get("quality_signals") or {}))
    text_safe = 1.0 if signals["text_safe_area_pass"] else 0.0
    first_frame = 1.0 if qa.get("first_frame") and not signals["generic_fullscreen_card"] else 0.0
    return {
        "content_id": content_id,
        "format": "shorts",
        "signals": signals,
        "dimensions": {
            "technical_delivery": {"value": 1.0 if qa.get("all_green") else 0.0,
                                   "evidence": "short technical QA"},
            "truth_and_evidence": {"value": 1.0, "evidence": "shorts gate passed"},
            "first_frame_and_hook": {"value": first_frame,
                                     "evidence": qa.get("first_frame", "missing")},
            "typography_and_safe_area": {"value": text_safe,
                                         "evidence": qa.get("caption_sheet", "missing")},
            "transition_motivation": {"value": 1.0 if transitions_ok else .45,
                                      "evidence": "sequence cut_motivation"},
            "rhythm_and_flow": {"value": 1.0 if visual_plan.get("energy_curve") else .6,
                                "evidence": "energy curve + duration gate"},
            "asset_novelty": {"value": max(0.0, 1.0 - fatigue["peak"]),
                              "evidence": json.dumps(fatigue)},
            "narrative_differentiation": {
                "value": max(0.0, 1.0 - narrative["peak_similarity"]),
                "evidence": json.dumps(narrative),
            },
            "tracking_and_compositing": {
                "value": 1.0 if tracking_ok else 0.0,
                "evidence": (
                    "verified tracked label/subject lock/matte sheen + GREEN report"
                    if tracking_present else
                    ("not required by routed content spec" if not tracking_required
                     else "required tracking/subject lock is missing")
                ),
            },
            "human_aesthetic_review": {"value": 0.0,
                                       "evidence": "pending Hao review"},
        },
        "human_review": {"completed": False},
        "narrative": narrative,
        "fatigue": fatigue,
        "signature": signature,
    }


def longform_evidence(*, content_id: str, delivery_qa: dict,
                      pacing_report: dict | None = None,
                      grade_report: dict | None = None) -> dict:
    """Adapt the existing longform delivery gate into the shared 95 contract."""
    linebreaks = (delivery_qa.get("linebreaks") or {}).get("ok")
    pacing = pacing_report or delivery_qa.get("scene_pacing") or {}
    grade = grade_report or {}
    visual_evidence = bool(
        delivery_qa.get("fullframe_sheets") or delivery_qa.get("contact_sheet"))
    signals = {
        "generic_fullscreen_card": False,
        "grid_used_as_default_opener": False,
        "template_role_label_visible": False,
        "unmotivated_geometric_transition": False,
        "text_safe_area_pass": linebreaks is not False,
        "persistent_location_strip": False,
        "content_has_location_value": False,
        "tracked_label_present": False,
        "tracked_label_has_evidence": True,
        "narrative_similarity_high": False,
        "asset_fatigue_high": False,
        "style_domain_match": True,
        "exact_reference_layout_copy": False,
        "visual_density_overload": False,
    }
    return {
        "content_id": content_id,
        "format": "longform",
        "signals": signals,
        "dimensions": {
            "technical_delivery": {
                "value": 1.0 if delivery_qa.get("deliver_ok") else 0.0,
                "evidence": "final_delivery_qa",
            },
            "truth_and_evidence": {
                "value": .9, "evidence": "proof still requires source review"},
            "first_frame_and_hook": {
                "value": .85 if visual_evidence else .55,
                "evidence": "fullframe/contact sheets",
            },
            "typography_and_safe_area": {
                "value": 1.0 if linebreaks is not False else 0.0,
                "evidence": "caption linebreak gate",
            },
            "transition_motivation": {
                "value": .9 if not delivery_qa.get("flash_flag") else .4,
                "evidence": "flash/artifact gate; motivation awaits review",
            },
            "rhythm_and_flow": {
                "value": 1.0 if pacing.get("ok") is True else .9,
                "evidence": "scene pacing + Hao review",
            },
            "asset_novelty": {
                "value": 1.0, "evidence": "no fatigue signal in delivery report"},
            "narrative_differentiation": {
                "value": .8, "evidence": "requires editorial comparison"},
            "tracking_and_compositing": {
                "value": 1.0 if grade.get("ok", True) else .5,
                "evidence": "grade/composite consistency",
            },
            "human_aesthetic_review": {
                "value": 0.0, "evidence": "pending Hao review"},
        },
        "human_review": {"completed": False},
        "signature": str(content_id),
    }


def write_report(output_dir: str | Path, evidence: dict,
                 *, remember_narrative: bool = False) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report = score_quality(evidence)
    report["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    json_path = output_dir / "QUALITY_95.json"
    _atomic_json(json_path, {**report, "evidence": evidence})
    lines = ["# Quality 95", "", f"- 狀態：**{report['status']}**",
             f"- 分數：**{report['score']} / 100**（目標 {report['target']}）", "",
             "## 維度"]
    lines.extend("- %s：%.1f / %s — %s" %
                 (row["id"], row["points"], row["weight"], row["evidence"])
                 for row in report["dimensions"])
    if report["negative_regressions"]:
        lines += ["", "## 回歸命中"] + [
            "- [%s] %s：%s" % (row["severity"], row["id"], row["message"])
            for row in report["negative_regressions"]]
    lines += ["", "> 機械檢查只能擋已知爛法；由 Hao 完成時間碼審片後才能取得 CERTIFIED_95，審片裝置不限。", ""]
    (output_dir / "QUALITY_95.md").write_text("\n".join(lines), encoding="utf-8")
    if remember_narrative and report["status"] != "BLOCKED" and evidence.get("signature"):
        record_narrative(evidence["content_id"], evidence["signature"])
    report["json"] = str(json_path)
    report["markdown"] = str(output_dir / "QUALITY_95.md")
    return report


def apply_human_review(evidence: dict, review: dict) -> dict:
    evidence = json.loads(json.dumps(evidence, ensure_ascii=False))
    aesthetic = score_aesthetic_review(
        review, format=evidence.get("format", "shorts"),
        signals=evidence.get("signals") or {},
    )
    evidence["dimensions"]["human_aesthetic_review"] = {
        "value": max(0.0, min(1.0, float(aesthetic["score"]) / 100.0)),
        "evidence": "Hao aesthetic standard %.1f/100 (%s)" %
                    (aesthetic["score"], aesthetic["status"]),
    }
    evidence["human_review"] = {
        "completed": bool(aesthetic["completed"]),
        "average": round(float(aesthetic["score"]) / 20.0, 2),
        "review_id": review.get("review_id"),
    }
    evidence["aesthetic_review"] = aesthetic
    return evidence


def self_test() -> None:
    dimensions = {name: 1.0 for name in load_corpus()["dimensions"]}
    clean = {"dimensions": dimensions, "signals": {"text_safe_area_pass": True},
             "human_review": {"completed": True},
             "aesthetic_review": {"status": "PASSED", "score": 100}}
    assert score_quality(clean)["status"] == "CERTIFIED_95"
    pending = json.loads(json.dumps(clean))
    pending["human_review"] = {"completed": False}
    pending["dimensions"]["human_aesthetic_review"] = 0
    assert score_quality(pending)["status"] == "REVIEW"
    bad = json.loads(json.dumps(clean))
    bad["signals"]["generic_fullscreen_card"] = True
    assert score_quality(bad)["status"] == "BLOCKED"
    aesthetic_bad = json.loads(json.dumps(clean))
    aesthetic_bad["aesthetic_review"] = {"status": "BLOCKED", "score": 65}
    assert score_quality(aesthetic_bad)["status"] == "BLOCKED"
    with tempfile.TemporaryDirectory(prefix="quality-95-adapters-") as temp:
        short = short_evidence(
            content_id="selftest-short",
            spec={"name": "測試", "what": "對決", "place": "競技場", "addr": "台灣",
                  "persistent_label_policy": "required"},
            ready={"caps": [(0, 1, [("開打", "white")], "hook")]},
            qa={"all_green": True, "first_frame": "first.jpg",
                "caption_sheet": "captions.jpg"},
            visual_plan={"energy_curve": [1], "sequence_plan": [
                {"cut_motivation": "action_or_information_change"}]},
            project_root=temp,
        )
        assert short["format"] == "shorts" and short["dimensions"]
        assert score_quality(short)["status"] == "REVIEW"
    long = longform_evidence(content_id="selftest-long", delivery_qa={
        "deliver_ok": True, "linebreaks": {"ok": True},
        "contact_sheet": "contact.jpg", "scene_pacing": {"ok": True},
    })
    assert long["format"] == "longform" and long["dimensions"]
    assert score_quality(long)["status"] == "REVIEW"
    print("quality_95 self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest")
    score = sub.add_parser("score")
    score.add_argument("evidence")
    score.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    if args.command == "selftest":
        self_test()
        return 0
    evidence = _read_json(Path(args.evidence), {})
    report = write_report(args.output_dir, evidence)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
