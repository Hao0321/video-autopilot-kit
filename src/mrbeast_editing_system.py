# -*- coding: utf-8 -*-
"""Evidence-gated high-information editing grammar.

The system abstracts observable functions from user-provided frames and the
official MrBeast video reference.  It does not reproduce logos, proprietary
assets, exact timelines or a creator's identity.  Every effect is an editorial
event with prerequisites, a narrative reason and a frame-QA contract.
"""
from __future__ import annotations

import argparse
import json
from typing import Any

from mrbeast_source_map import load_map, validate_map


EVENTS = {
    "promise_cold_open": {
        "function": "state the scale, conflict or result before context",
        "requires": ["real_payoff_or_conflict_shot"],
        "duration": [.35, 2.5],
        "visual": ["hero footage", "selective claim", "single tension cue"],
    },
    "value_label": {
        "function": "make a verified number instantly legible beside its subject",
        "requires": ["numeric_evidence", "subject_track_or_verified_keyframes"],
        "duration": [.35, 1.8],
        "visual": ["editable CJK/Latin/numeric type", "depth shadow", "optional scanline", "subject-relative anchor"],
    },
    "challenge_ledger": {
        "function": "preserve progress and stakes without verbal repetition",
        "requires": ["state_items", "state_change_timestamps"],
        "duration": [1.0, 999.0],
        "visual": ["top-left compact record", "active/completed/upcoming states", "subject thumbnail only with licence"],
    },
    "tracked_callout": {
        "function": "locate the exact object or evidence being discussed",
        "requires": ["initial_bbox_or_polygon", "track_report", "visibility_window"],
        "duration": [.35, 2.0],
        "visual": ["label", "pointer or bracket", "subject motion follow", "hide on track loss"],
    },
    "subject_sheen": {
        "function": "turn a hero object reveal into a premium material event",
        "requires": ["subject_matte", "track_or_keyframes", "material_profile", "frame_qa"],
        "duration": [.25, .60],
        "visual": ["diagonal core band", "soft secondary bloom", "matte-clipped specular response", "no full-frame flash"],
    },
    "money_burst": {
        "function": "punctuate a verified monetary payoff",
        "requires": ["currency_evidence", "licensed_or_generated_usd_particle_asset", "payoff_timestamp"],
        "duration": [.35, 1.2],
        "visual": ["USD particle overlay", "depth layers", "gravity and drag", "never a transition"],
    },
    "scale_ladder": {
        "function": "compare multiple levels under one shared baseline",
        "requires": ["ordered_values", "comparable_visuals", "scale_evidence"],
        "duration": [1.2, 8.0],
        "visual": ["consistent labels", "progressive reveal", "overview payoff"],
    },
    "subject_occlusion_cut": {
        "function": "hide a motivated cut behind a real foreground subject",
        "requires": ["shot_a", "shot_b", "same_direction_motion", "verified_occlusion_frame", "actual_cut_timestamp"],
        "duration": [.08, .35],
        "visual": ["real occluder", "direction continuity", "audio bridge"],
    },
    "whip_replacement": {
        "function": "replace one comparable object during a matched camera move",
        "requires": ["shot_a", "shot_b", "direction_match", "motion_blur_match", "cut_timestamp"],
        "duration": [.12, .45],
        "visual": ["same screen direction", "compatible scale", "brief motion-blur cover"],
    },
    "fast_pullback_reveal": {
        "function": "reveal scale by changing spatial context rather than adding decoration",
        "requires": ["wide_context_footage_or_true_3d_scene", "camera_path_evidence"],
        "duration": [.35, 2.0],
        "visual": ["close-to-wide spatial reveal", "parallax", "hero remains readable"],
    },
    "proof_freeze": {
        "function": "give viewers enough time to verify the result",
        "requires": ["proof_frame", "source_id"],
        "duration": [.45, 2.5],
        "visual": ["clean hold", "one annotation maximum", "sound emphasis optional"],
    },
    "breath_reset": {
        "function": "restore contrast before escalation or payoff",
        "requires": ["energy_curve_position"],
        "duration": [.35, 3.0],
        "visual": ["reduced graphics", "room tone", "longer shot"],
    },
}
BLOCKED_SUBSTITUTIONS = {
    "full_frame_flash_for_subject_sheen": "A subject sheen must stay inside the moving matte.",
    "money_particles_as_transition": "Money is a payoff overlay, not a cut type.",
    "generic_grid_opener": "A grid is optional information scaffolding, never the opening reason.",
    "fake_tracking": "No path may be invented after a tracker loses the subject.",
    "empty_fullscreen_template": "Usable footage cannot be replaced by a generic role card.",
    "effect_every_cut": "Visual events need semantic change and contrast gaps.",
}


def plan_sequence(beats: list[dict[str, Any]], *, format: str = "shorts",
                  effect_budget: int | None = None) -> dict[str, Any]:
    source_map = load_map()
    source_map_errors = validate_map(source_map)
    if source_map_errors:
        raise ValueError("invalid MrBeast source map: " + "; ".join(source_map_errors))
    format_key = "longform" if str(format).lower() in {"long", "longform", "youtube"} else "shorts"
    budget = int(effect_budget if effect_budget is not None else (4 if format_key == "shorts" else 10))
    selected, blocked = [], []
    last_effect_time = -999.0
    minimum_gap = .45 if format_key == "shorts" else 1.0
    for index, beat in enumerate(beats):
        event = str(beat.get("event", ""))
        if event not in EVENTS:
            blocked.append({"index": index, "event": event, "reason": "unknown_event"})
            continue
        timestamp = float(beat.get("time", 0))
        evidence = set(beat.get("evidence") or [])
        missing = [key for key in EVENTS[event]["requires"] if key not in evidence]
        if missing:
            blocked.append({"index": index, "event": event, "reason": "missing_evidence", "missing": missing})
            continue
        if len(selected) >= budget:
            blocked.append({"index": index, "event": event, "reason": "effect_budget_exhausted"})
            continue
        if event not in {"promise_cold_open", "challenge_ledger", "breath_reset"} and timestamp - last_effect_time < minimum_gap:
            blocked.append({"index": index, "event": event, "reason": "contrast_gap_too_short"})
            continue
        selected.append({
            "time": timestamp, "event": event,
            "function": EVENTS[event]["function"],
            "duration_range": EVENTS[event]["duration"],
            "visual_contract": EVENTS[event]["visual"],
            "evidence": sorted(evidence),
        })
        if event not in {"challenge_ledger"}:
            last_effect_time = timestamp
    return {
        "schema_version": 1,
        "system": "hao-high-information-editing-v1",
        "format": format_key,
        "selected": selected,
        "blocked": blocked,
        "effect_budget": budget,
        "used": len(selected),
        "principles": [
            "clarity before stimulation; one idea and one emotion at a time",
            "promise and proof before decoration",
            "large numbers and labels are information events, not subtitles",
            "tracking, masking and 3D are evidence-gated",
            "contrast between impact and breath creates perceived pace",
            "motion graphics, tracking, 3D and VFX remain separate production classes",
            "all surface treatment remains Hao-original and asset-licensed",
        ],
        "source_map_version": source_map.get("version"),
        "blocked_substitutions": BLOCKED_SUBSTITUTIONS,
    }


def validate_plan(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if int(plan.get("used", 0)) > int(plan.get("effect_budget", 0)):
        errors.append("effect budget exceeded")
    for row in plan.get("selected", []):
        if row.get("event") not in EVENTS:
            errors.append("unknown selected event")
        if not row.get("evidence"):
            errors.append("selected event has no evidence")
    sheen = [row for row in plan.get("selected", []) if row.get("event") == "subject_sheen"]
    for row in sheen:
        required = {"subject_matte", "track_or_keyframes", "material_profile", "frame_qa"}
        if not required.issubset(row.get("evidence") or []):
            errors.append("subject sheen missing matte, track, material or frame QA")
    return errors


def self_test() -> None:
    beats = [
        {"time": 0, "event": "promise_cold_open", "evidence": ["real_payoff_or_conflict_shot"]},
        {"time": .8, "event": "subject_sheen", "evidence": [
            "subject_matte", "track_or_keyframes", "material_profile", "frame_qa"]},
        {"time": 1.5, "event": "money_burst", "evidence": ["currency_evidence"]},
        {"time": 2.2, "event": "proof_freeze", "evidence": ["proof_frame", "source_id"]},
    ]
    plan = plan_sequence(beats, format="shorts")
    assert [row["event"] for row in plan["selected"]] == ["promise_cold_open", "subject_sheen", "proof_freeze"]
    assert any(row["event"] == "money_burst" and row["reason"] == "missing_evidence" for row in plan["blocked"])
    assert not validate_plan(plan)
    assert plan["source_map_version"] == "2026-08-13"
    assert "full_frame_flash_for_subject_sheen" in BLOCKED_SUBSTITUTIONS
    print("mrbeast_editing_system self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan evidence-gated high-information visual events")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest")
    plan = sub.add_parser("plan")
    plan.add_argument("beats")
    plan.add_argument("--format", default="shorts")
    plan.add_argument("--effect-budget", type=int, default=None)
    args = parser.parse_args(argv)
    if args.command == "selftest":
        self_test()
        return 0
    beats = json.loads(open(args.beats, encoding="utf-8").read())
    output = plan_sequence(beats, format=args.format, effect_budget=args.effect_budget)
    output["errors"] = validate_plan(output)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 1 if output["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
