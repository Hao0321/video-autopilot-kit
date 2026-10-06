# -*- coding: utf-8 -*-
"""Quality-95 certification layer for short and long video delivery.

Mechanical checks can reject known failures.  Only a timestamped human review
can certify taste.  Reports therefore separate provisional machine confidence
from the final 95/100 certification instead of pretending green tests equal art.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import os
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from asset_memory import asset_fatigue_report
from aesthetic_score import review_schema
from aesthetic_score import score_review as score_aesthetic_review
from project_paths import discover_project_root
from quality_corpus import detect_negative, load_corpus, narrative_similarity


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = discover_project_root(ROOT)
NARRATIVE_STATE = PROJECT_ROOT / "videos" / "_state" / "quality_narratives.json"
REVIEW_KEY_ENV = "VIDEO_AUTOPILOT_REVIEW_KEY"
# Signals a spec may only make stricter: a good signal can be lowered, never raised.
GOOD_SIGNALS = frozenset({"text_safe_area_pass", "style_domain_match", "design_dna_compiled",
                          "tracked_label_has_evidence"})


def review_key_path() -> Path:
    explicit = os.environ.get(REVIEW_KEY_ENV, "").strip()
    return Path(explicit).expanduser() if explicit else Path.home() / ".video-autopilot" / "review-signing.key"


def _review_key(create: bool = False) -> bytes | None:
    """Per-machine HMAC key held by the review server, never inside a project."""
    path = review_key_path()
    if create and not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            handle = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(handle, "w", encoding="ascii") as stream:
                stream.write(secrets.token_hex(32))
    try:
        key = path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeDecodeError):
        return None
    return key.encode("ascii") if len(key) >= 32 else None


def _review_mac(key: bytes, review: dict) -> str:
    body = {name: value for name, value in review.items() if name != "receipt"}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()


def stamp_review(review: dict, artifact_sha256: str) -> dict:
    """Review-server stamp binding a saved review to the exact reviewed bytes."""
    key = _review_key(create=True)
    if key is None:
        raise RuntimeError("review signing key is unavailable")
    stamped = {name: value for name, value in review.items() if name != "receipt"}
    stamped["artifact_sha256"] = str(artifact_sha256 or "")
    stamped["receipt"] = _review_mac(key, stamped)
    return stamped


def verify_review(review: Any, artifact_sha256: str | None = None) -> str:
    """Return '' for a submitted, server-stamped review of ``artifact_sha256``."""
    if not isinstance(review, dict) or not review.get("completed_at"):
        return "review was not submitted from the review page (completed_at missing)"
    key = _review_key()
    receipt = review.get("receipt")
    if key is None or not isinstance(receipt, str):
        return "review is not stamped by the review server"
    if not hmac.compare_digest(receipt, _review_mac(key, review)):
        return "review stamp does not verify (edited after submission)"
    if not review.get("artifact_sha256") or (
            artifact_sha256 is not None and review.get("artifact_sha256") != artifact_sha256):
        return "review belongs to a different render of this video"
    return ""


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


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _value(evidence: dict, name: str) -> tuple[float, str]:
    raw = evidence.get("dimensions", {}).get(name)
    if isinstance(raw, dict):
        number = _finite(raw.get("value", 0))
        if number is None:
            return 0.0, "invalid value"
        return max(0.0, min(1.0, number)), str(raw.get("evidence", ""))
    if isinstance(raw, bool):
        return (1.0 if raw else 0.0), "boolean evidence"
    number = _finite(raw)
    if number is not None:
        return max(0.0, min(1.0, number)), "numeric evidence"
    return 0.0, "missing" if raw is None else "invalid value"


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
    gaps = [row["id"] for row in rows if row["evidence"] in {"missing", "invalid value"}
            or str(row["evidence"]).startswith("GAP:")]
    if gaps:
        # Missing evidence is not a failure, but it can never certify.
        hits.append({"id": "evidence-gap", "severity": "REVIEW",
                     "message": "Evidence missing or invalid for: " + ", ".join(gaps)})
    blocks = [row for row in hits if row["severity"] == "BLOCK"]
    reviews = [row for row in hits if row["severity"] == "REVIEW"]
    human_value, _ = _value(evidence, "human_aesthetic_review")
    human = dict(evidence.get("human_review") or {})
    review_problem = verify_review(human.get("review"), human.get("artifact_sha256"))
    human_complete = bool(human.get("completed")) and human_value > 0 and not review_problem
    aesthetic = dict(evidence.get("aesthetic_review") or {})
    if human.get("completed") and not review_problem:
        # Certification follows the verified review itself, not a copied status field.
        aesthetic = score_aesthetic_review(human["review"], format=evidence.get("format", "shorts"),
                                           signals=signals)
    elif human.get("completed"):
        unverified = {"id": "human-review-unverified", "severity": "REVIEW",
                      "message": "Human review cannot certify: " + review_problem}
        reviews.append(unverified)
        hits.append(unverified)
    aesthetic_status = aesthetic.get("status", "REVIEW")
    if aesthetic_status == "BLOCKED":
        aesthetic_hit = {"id": "aesthetic-review-blocked", "severity": "BLOCK",
                         "message": "Creator aesthetic review contains a blocker or scores below 70."}
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
        "certification_rule": ("score>=95 + server-stamped creator review of this exact render "
                               "PASSED + no BLOCK/REVIEW regression"),
    }


def _short_signature(spec: dict, ready: dict) -> str:
    caption_text = " ".join(
        "".join(str(text) for text, _color in blocks)
        for _start, _end, blocks, kind in ready.get("caps", []) if kind != "addr"
    )
    return " ".join((str(spec.get("name", "")), str(spec.get("what", "")), caption_text))


def _tracking_quality(spec: dict, tracked_report: dict | None) -> tuple[bool, bool, bool, bool]:
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
    return tracking_present, tracking_required, tracking_evidence, tracking_ok


def _parallax_quality(spec: dict, parallax_report: dict | None) -> tuple[bool, bool]:
    parallax_config = spec.get("parallax_transition") or {}
    parallax_present = bool(parallax_config)
    parallax_required = {
        "two_real_source_shots", "outgoing_foreground_mattes",
        "incoming_foreground_mattes", "reconstructed_backgrounds",
        "matched_motion_direction", "explicit_cut_frame", "foreground_edge_qa",
    }
    parallax_evidence = set(parallax_config.get("evidence") or [])
    parallax_ok = (
        not parallax_present or
        (parallax_required.issubset(parallax_evidence) and
         bool(parallax_report and parallax_report.get("status") == "GREEN") and
         parallax_report.get("foreground_cut_policy") ==
         "midpoint_hard_handoff_no_double_subject_dissolve")
    )
    return parallax_present, parallax_ok


def _short_signals(
    spec: dict, qa: dict, visual_plan: dict, narrative: dict, fatigue: dict,
    tracking_present: bool, tracking_required: bool, tracking_evidence: bool,
    parallax_present: bool, parallax_ok: bool,
) -> dict:
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
        "design_dna_compiled": bool((visual_plan.get("design_system_v6") or {}).get("compiler")),
        "subject_sheen_leaks_outside_matte": False,
        "subject_sheen_used_as_transition": False,
        "subject_reveal_not_full_black_at_start": False,
        "subject_reveal_restores_outside_matte": False,
        "tracked_telemetry_drift_or_jitter": False,
        "tracked_telemetry_value_without_evidence": False,
        "parallax_double_subject_ghost": False,
        "parallax_matte_halo": False,
        "parallax_transition_missing_real_shot_pair": parallax_present and not parallax_ok,
        "parallax_chromatic_aberration_persistent": False,
        "fake_3d_claim": False,
        "3d_light_or_shadow_mismatch": False,
    }
    for key, value in dict(spec.get("quality_signals") or {}).items():
        # A spec may report extra problems or withdraw a pass, never self-certify one.
        if key in GOOD_SIGNALS:
            signals[key] = bool(signals.get(key, False)) and value is True
        else:
            signals[key] = bool(signals.get(key, False)) or value is True
    return signals


def _short_dimensions(
    qa: dict, visual_plan: dict, signals: dict, fatigue: dict, narrative: dict,
    tracking_present: bool, tracking_required: bool, tracking_ok: bool,
    parallax_present: bool, parallax_ok: bool,
) -> dict:
    sequences = visual_plan.get("sequence_plan") or []
    transitions_ok = all(row.get("cut_motivation") in {
        "action_or_information_change", "hold_for_contrast", "matched_motion",
        "occlusion", "spatial_continuity"
    } for row in sequences)
    compositing_ok = tracking_ok and parallax_ok
    compositing_evidence = (
        "verified tracking/matte and parallax prerequisites + GREEN reports"
        if tracking_present or parallax_present else
        ("not required by routed content spec" if not tracking_required
         else "required tracking/subject lock is missing")
    )
    return {
        "technical_delivery": {"value": 1.0 if qa.get("all_green") else 0.0,
                               "evidence": "short technical QA"},
        "truth_and_evidence": {"value": 1.0, "evidence": "shorts gate passed"},
        "first_frame_and_hook": {
            "value": 1.0 if qa.get("first_frame") and not signals["generic_fullscreen_card"] else 0.0,
            "evidence": qa.get("first_frame", "missing"),
        },
        "typography_and_safe_area": {
            "value": 1.0 if signals["text_safe_area_pass"] else 0.0,
            "evidence": qa.get("caption_sheet", "missing"),
        },
        "transition_motivation": {"value": 1.0 if transitions_ok else .45,
                                  "evidence": "sequence cut_motivation" if sequences
                                  else "GAP: no sequence plan recorded"},
        "rhythm_and_flow": {"value": 1.0 if visual_plan.get("energy_curve") else .6,
                            "evidence": "energy curve + duration gate"},
        "asset_novelty": {"value": max(0.0, 1.0 - fatigue["peak"]),
                          "evidence": json.dumps(fatigue)},
        "narrative_differentiation": {
            "value": max(0.0, 1.0 - narrative["peak_similarity"]),
            "evidence": json.dumps(narrative),
        },
        "tracking_and_compositing": {"value": 1.0 if compositing_ok else 0.0,
                                     "evidence": compositing_evidence},
        "human_aesthetic_review": {"value": 0.0, "evidence": "pending creator review"},
    }


def short_evidence(*, content_id: str, spec: dict, ready: dict, qa: dict,
                   visual_plan: dict, tracked_report: dict | None = None,
                   parallax_report: dict | None = None,
                   project_root: str | Path = PROJECT_ROOT) -> dict:
    """Adapt a rendered Short into the shared Quality-95 evidence contract."""
    signature = _short_signature(spec, ready)
    narrative = narrative_report(content_id, signature)
    selected = (visual_plan.get("asset_intelligence") or {}).get("selected_bgm_asset_id")
    fatigue = asset_fatigue_report([selected] if selected else [], project_root)
    tracking_present, tracking_required, tracking_evidence, tracking_ok = _tracking_quality(
        spec, tracked_report)
    parallax_present, parallax_ok = _parallax_quality(spec, parallax_report)
    signals = _short_signals(
        spec, qa, visual_plan, narrative, fatigue, tracking_present,
        tracking_required, tracking_evidence, parallax_present, parallax_ok,
    )
    return {
        "content_id": content_id,
        "format": "shorts",
        "signals": signals,
        "dimensions": _short_dimensions(
            qa, visual_plan, signals, fatigue, narrative, tracking_present,
            tracking_required, tracking_ok, parallax_present, parallax_ok,
        ),
        "human_review": {"completed": False},
        "narrative": narrative,
        "fatigue": fatigue,
        "signature": signature,
    }


def longform_evidence(*, content_id: str, delivery_qa: dict,
                      pacing_report: dict | None = None,
                      grade_report: dict | None = None,
                      visual_plan: dict | None = None) -> dict:
    """Adapt the existing longform delivery gate into the shared 95 contract."""
    linebreaks = (delivery_qa.get("linebreaks") or {}).get("ok")
    pacing = pacing_report or delivery_qa.get("scene_pacing") or {}
    grade = grade_report or {}
    visual_plan = visual_plan or {}
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
        "design_dna_compiled": str(
            (visual_plan.get("design_system_v6") or {}).get("compiler") or ""
        ).endswith("design-system-v6"),
        "subject_sheen_leaks_outside_matte": False,
        "subject_sheen_used_as_transition": False,
        "subject_reveal_not_full_black_at_start": False,
        "subject_reveal_restores_outside_matte": False,
        "tracked_telemetry_drift_or_jitter": False,
        "tracked_telemetry_value_without_evidence": False,
        "parallax_double_subject_ghost": False,
        "parallax_matte_halo": False,
        "parallax_transition_missing_real_shot_pair": False,
        "parallax_chromatic_aberration_persistent": False,
        "fake_3d_claim": False,
        "3d_light_or_shadow_mismatch": False,
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
                "evidence": "caption linebreak gate" if linebreaks is not None
                else "GAP: caption linebreak gate not run",
            },
            "transition_motivation": {
                "value": .9 if not delivery_qa.get("flash_flag") else .4,
                "evidence": "flash/artifact gate; motivation awaits review",
            },
            "rhythm_and_flow": {
                "value": 1.0 if pacing.get("ok") is True else .9,
                "evidence": "scene pacing + creator review",
            },
            "asset_novelty": {
                "value": 1.0, "evidence": "no fatigue signal in delivery report"},
            "narrative_differentiation": {
                "value": .8, "evidence": "requires editorial comparison"},
            "tracking_and_compositing": {
                "value": 1.0 if grade.get("ok", True) else .5,
                "evidence": "grade/composite consistency" if grade
                else "GAP: no grade report",
            },
            "human_aesthetic_review": {
                "value": 0.0, "evidence": "pending creator review"},
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
    lines += ["", "> 機械檢查只能擋已知爛法；由創作者（或其指定審片者）在審片頁完成這一版的時間碼審片後，才能取得 CERTIFIED_95，審片裝置不限。", ""]
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
        "evidence": "Creator aesthetic standard %.1f/100 (%s)" %
                    (aesthetic["score"], aesthetic["status"]),
    }
    evidence["human_review"] = {
        "completed": bool(aesthetic["completed"]),
        "average": round(float(aesthetic["score"]) / 20.0, 2),
        "review_id": review.get("review_id"),
        "artifact_sha256": review.get("artifact_sha256"),
        "review": review,
    }
    evidence["aesthetic_review"] = aesthetic
    return evidence


def _self_test_review_receipts(clean: dict) -> dict:
    """Only a server-stamped, submitted review of the same render can certify."""
    ratings = {key: 5 for key in review_schema("shorts")["dimensions"]}
    review = {"review_id": "selftest", "ratings": ratings, "issues": [],
              "completed_at": "selftest-submitted"}
    forged = score_quality(clean)
    assert forged["status"] == "REVIEW", "self-written evidence must not certify"
    assert any(hit["id"] == "human-review-unverified" for hit in forged["negative_regressions"])
    stamped = stamp_review(review, "a" * 64)
    certified = apply_human_review({key: value for key, value in clean.items()
                                    if key not in {"human_review", "aesthetic_review"}}, stamped)
    assert score_quality(certified)["status"] == "CERTIFIED_95"
    tampered = json.loads(json.dumps(certified))
    tampered["human_review"]["review"]["ratings"][next(iter(ratings))] = 1
    assert score_quality(tampered)["status"] != "CERTIFIED_95", "edited review must not certify"
    draft = apply_human_review(clean, stamp_review(dict(review, completed_at=""), "a" * 64))
    assert score_quality(draft)["status"] != "CERTIFIED_95", "autosaved draft must not certify"
    assert verify_review(stamped, "b" * 64), "a review of another render must not verify"
    nan = json.loads(json.dumps(certified))
    nan["dimensions"]["technical_delivery"] = float("nan")
    assert score_quality(nan)["status"] != "CERTIFIED_95" and _value(nan, "technical_delivery")[0] == 0.0
    return certified


def self_test() -> None:
    dimensions = {name: 1.0 for name in load_corpus()["dimensions"]}
    forged = {"format": "shorts", "dimensions": dimensions, "signals": {"text_safe_area_pass": True},
              "human_review": {"completed": True},
              "aesthetic_review": {"status": "PASSED", "score": 100}}
    previous_key = os.environ.get(REVIEW_KEY_ENV)
    key_dir = tempfile.TemporaryDirectory(prefix="quality-95-key-")
    os.environ[REVIEW_KEY_ENV] = str(Path(key_dir.name) / "review-signing.key")
    try:
        clean = _self_test_review_receipts(forged)
    finally:
        if previous_key is None:
            os.environ.pop(REVIEW_KEY_ENV, None)
        else:
            os.environ[REVIEW_KEY_ENV] = previous_key
        key_dir.cleanup()
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
    long = longform_evidence(
        content_id="selftest-long",
        delivery_qa={
            "deliver_ok": True, "linebreaks": {"ok": True},
            "contact_sheet": "contact.jpg", "scene_pacing": {"ok": True},
        },
        visual_plan={"design_system_v6": {"compiler": "hao-design-system-v6"}},
    )
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
