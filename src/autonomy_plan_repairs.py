"""Public workflow component (public distribution).

Configurable source-only workflow implementation; no creator data or live capability proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any


REJECTED_EFFECT_STATES = {"AWAITING_EVIDENCE", "PENDING", "REJECTED", "BLOCKED", "MISSING_EVIDENCE"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repair(ledger: list[dict[str, Any]], path: str, before: Any, after: Any,
            reason: str) -> None:
    ledger.append({"path": path, "before": before, "after": after,
                   "reason": reason, "reversible": True})


def _repair_transitions(plan: dict[str, Any], repairs: list[dict[str, Any]]) -> None:
    craft = plan.get("mediastorm_craft") or {}
    transitions = ((craft.get("editing") or {}).get("transitions") or [])
    for index, row in enumerate(transitions):
        missing = list(row.get("missing") or [])
        status = str(row.get("status") or "").upper()
        if missing or status not in {"READY", ""}:
            before = row.get("selected")
            if before != "clean_cut":
                row["selected"] = "clean_cut"
                row["status"] = "DOWNGRADED"
                _repair(repairs, f"mediastorm_craft.editing.transitions[{index}].selected",
                        before, "clean_cut", "unverified transition prerequisites")


def _repair_information(plan: dict[str, Any], repairs: list[dict[str, Any]]) -> None:
    info = plan.get("high_information_system") or {}
    selected, kept, newly_blocked = list(info.get("selected") or []), [], []
    for index, row in enumerate(selected):
        event = str(row.get("event") or "unknown")
        evidence = set(row.get("evidence") or [])
        required = {
            "subject_sheen": {"subject_matte", "track_or_keyframes", "material_profile", "frame_qa"},
            "black_to_color_subject_reveal": {
                "per_frame_subject_matte", "track_or_keyframes", "material_profile",
                "first_mid_last_frame_qa", "occlusion_edge_review",
            },
            "tracked_callout": {"initial_bbox_or_polygon", "track_report", "visibility_window"},
            "tracked_telemetry_callout": {
                "initial_bbox_or_polygon", "track_report", "visibility_window",
                "measured_value_evidence", "connector_anchor_shared_track",
            },
            "money_burst": {"currency_evidence", "licensed_or_generated_usd_particle_asset", "payoff_timestamp"},
        }.get(event, set())
        if not evidence or not required.issubset(evidence):
            newly_blocked.append({"index": index, "event": event,
                                  "reason": "unattended_missing_evidence",
                                  "missing": sorted(required - evidence)})
            _repair(repairs, f"high_information_system.selected[{index}]", row, None,
                    "effect cannot be verified without inventing evidence")
        else:
            kept.append(row)
    if len(kept) != len(selected):
        info["selected"] = kept
        info["blocked"] = list(info.get("blocked") or []) + newly_blocked
        info["used"] = len(kept)
        info["status"] = "SAFE_FALLBACK" if newly_blocked else info.get("status")


def _repair_three_d(plan: dict[str, Any], repairs: list[dict[str, Any]]) -> None:
    three_d = plan.get("three_d_system") or {}
    if three_d and str(three_d.get("status") or "").upper() != "READY":
        before = three_d.get("execution_enabled", True)
        three_d["execution_enabled"] = False
        if before is not False:
            _repair(repairs, "three_d_system.execution_enabled", before, False,
                    "3D route lacks production prerequisites")


def _repair_motion(plan: dict[str, Any], repairs: list[dict[str, Any]]) -> None:
    motion = plan.get("motion_assets") or {}
    cues = list(motion.get("cues") or [])
    kept_cues = []
    for index, cue in enumerate(cues):
        status = str(cue.get("status") or "").upper()
        if status in REJECTED_EFFECT_STATES:
            _repair(repairs, f"motion_assets.cues[{index}]", cue, None,
                    "motion cue has no ready evidence")
        else:
            kept_cues.append(cue)
    if len(kept_cues) != len(cues):
        motion["cues"] = kept_cues


def _repair_color(plan: dict[str, Any], repairs: list[dict[str, Any]]) -> None:
    color = plan.get("color_system") or {}
    input_status = str(color.get("input_status") or color.get("source_status") or "").upper()
    if input_status in {"BLOCK_UNKNOWN_LOG", "UNKNOWN_LOG", "UNKNOWN_INPUT_TRANSFORM"}:
        before = color.get("creative_look_enabled", True)
        color["creative_look_enabled"] = False
        color["safe_fallback"] = "neutral_normalization_only"
        if before is not False:
            _repair(repairs, "color_system.creative_look_enabled", before, False,
                    "unknown input transform; creative look disabled")


def prepare_unattended_plan(visual_plan: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return a safe copy and a reversible repair ledger, never invented evidence."""
    plan = copy.deepcopy(visual_plan)
    repairs: list[dict[str, Any]] = []
    for repairer in (_repair_transitions, _repair_information, _repair_three_d,
                     _repair_motion, _repair_color):
        repairer(plan, repairs)
    plan["unattended_preflight"] = {
        "schema_version": 1,
        "policy": "reversible-downgrade-only",
        "repairs": len(repairs),
        "human_review_required": True,
        "certification_forbidden": True,
        "prepared_at": _now(),
    }
    return plan, repairs
