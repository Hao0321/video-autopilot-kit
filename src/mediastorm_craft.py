# -*- coding: utf-8 -*-
"""Evidence-gated 影視颶風 craft planner for long-form and short-form edits.

This module learns general, observable filmmaking craft from public work.  It
does not copy an edit, LUT, logo, project file, or unpublished preset.  Its
most important decision is often to keep a clean cut.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SYSTEM_ID = "hao-mediastorm-craft-v1"
KNOWLEDGE = Path(__file__).resolve().parent / "knowledge" / "mediastorm_craft_benchmark.json"


TRANSITION_CONTRACTS: dict[str, dict[str, Any]] = {
    "clean_cut": {
        "requires": [], "class": "invisible", "fallback": "clean_cut",
        "reason": "information, gaze, action or emotion changes",
    },
    "j_cut": {
        "requires": ["incoming_audio_clean", "dialogue_or_ambient_motivates_next_scene"],
        "class": "audio_bridge", "fallback": "clean_cut",
        "reason": "next scene is understood through sound before the picture changes",
    },
    "l_cut": {
        "requires": ["outgoing_audio_clean", "audio_tail_has_semantic_value"],
        "class": "audio_bridge", "fallback": "clean_cut",
        "reason": "the outgoing voice or environment carries meaning across the cut",
    },
    "cut_on_action": {
        "requires": ["outgoing_action_peak", "incoming_action_continuation", "screen_direction_match"],
        "class": "continuity", "fallback": "clean_cut",
        "reason": "one physical action hides the edit",
    },
    "match_cut": {
        "requires": ["matched_subject_anchor", "matched_scale_or_shape", "semantic_relation"],
        "class": "continuity", "fallback": "clean_cut",
        "reason": "shape, scale and meaning continue across two real shots",
    },
    "foreground_wipe": {
        "requires": ["foreground_occluder", "occlusion_over_70pct", "matched_exit_entry_direction"],
        "class": "motivated", "fallback": "clean_cut",
        "reason": "a photographed foreground object conceals the cut",
    },
    "whip_pan_cut": {
        "requires": ["outgoing_whip", "incoming_whip", "matched_whip_direction", "motion_blur_cover"],
        "class": "motivated", "fallback": "clean_cut",
        "reason": "camera momentum bridges space",
    },
    "speed_ramp_cut": {
        "requires": ["high_fps_source", "motion_peak", "ramp_preserves_subject_readability"],
        "class": "emphasis", "fallback": "cut_on_action",
        "reason": "a real movement earns acceleration or deceleration",
    },
    "graphic_match": {
        "requires": ["shared_graphic_anchor", "graphic_is_information_not_decoration"],
        "class": "information", "fallback": "clean_cut",
        "reason": "a diagram, label or frame geometry carries one idea between shots",
    },
    "dissolve_short": {
        "requires": ["time_or_emotion_shift", "low_motion_boundary"],
        "class": "temporal", "fallback": "clean_cut",
        "reason": "time or mood changes without breaking spatial comprehension",
    },
}


ALIASES = {
    "cut": "clean_cut", "impact_cut": "clean_cut", "punch": "clean_cut", "snap": "clean_cut",
    "audio_bridge": "j_cut", "match_action": "cut_on_action", "match_motion": "cut_on_action",
    "match_direction": "cut_on_action", "match_pose": "match_cut", "phrase_cut": "clean_cut",
    "cut_on_beat": "clean_cut", "screen_wipe": "graphic_match", "data_wipe": "graphic_match",
    "wipe": "foreground_wipe", "whip": "whip_pan_cut", "speed_ramp": "speed_ramp_cut",
    "glitch_once": "clean_cut",
}


DOMAIN_GRAMMAR = {
    "ai": ("result", "screen_context", "operation", "proof", "limitation"),
    "product": ("result", "hero", "control_detail", "measurement", "limitation", "verdict"),
    "toy": ("result", "hand_scale", "macro_detail", "action", "collision", "outcome"),
    "travel": ("destination", "geography", "human_scale", "movement", "local_detail", "quiet_hold"),
    "food": ("hero_texture", "place", "process", "macro_texture", "reaction", "verdict"),
    "interview": ("strong_quote", "speaker_context", "evidence", "hands_or_process", "pause", "takeaway"),
    "documentary": ("consequence", "place", "person", "observed_action", "evidence", "reaction"),
    "general": ("result", "context", "action", "detail", "turn", "payoff"),
}


def _normalize_format(value: str) -> str:
    return "shorts" if str(value).lower() in {"short", "shorts", "reels", "vertical"} else "longform"


def _transition_limit(duration: float, format_kind: str) -> int:
    if format_kind == "shorts":
        return max(1, min(2, round(duration / 20)))
    return max(2, min(5, round(duration / 45)))


def resolve_transition(requested: str, evidence: set[str] | list[str] | tuple[str, ...]) -> dict[str, Any]:
    normalized = ALIASES.get(str(requested or "clean_cut"), str(requested or "clean_cut"))
    if normalized not in TRANSITION_CONTRACTS:
        normalized = "clean_cut"
    contract = TRANSITION_CONTRACTS[normalized]
    available = set(evidence or [])
    missing = [item for item in contract["requires"] if item not in available]
    selected = normalized if not missing else contract["fallback"]
    if selected == "cut_on_action" and not {
        "outgoing_action_peak", "incoming_action_continuation", "screen_direction_match"
    }.issubset(available):
        selected = "clean_cut"
    return {
        "requested": requested or "clean_cut", "normalized": normalized,
        "selected": selected, "status": "READY" if not missing else "DOWNGRADED",
        "class": contract["class"], "missing": missing, "motivation": contract["reason"],
    }


def compile_craft_plan(*, duration: float, format: str, domain: str,
                       sequence_plan: list[dict[str, Any]] | None = None,
                       evidence: list[str] | set[str] | None = None,
                       seed: object = 0) -> dict[str, Any]:
    """Compile camera, edit, sound, colour and VFX craft into one compact plan."""
    duration = float(duration)
    if duration <= 0:
        raise ValueError("duration must be > 0")
    fmt = _normalize_format(format)
    rows = sequence_plan or []
    expressive_limit = _transition_limit(duration, fmt)
    expressive_used = 0
    transitions = []
    for index, row in enumerate(rows):
        decision = resolve_transition(str(row.get("transition_out", "clean_cut")), evidence or [])
        if decision["selected"] != "clean_cut":
            if expressive_used >= expressive_limit:
                decision.update({"selected": "clean_cut", "status": "DOWNGRADED",
                                 "budget_reason": "expressive_transition_budget_exhausted"})
            else:
                expressive_used += 1
        decision.update({"index": index, "act": row.get("act"), "at": row.get("end")})
        transitions.append(decision)
    digest = hashlib.sha256(
        f"{duration}|{fmt}|{domain}|{seed}|{len(rows)}".encode("utf-8")
    ).hexdigest()[:12]
    grammar = DOMAIN_GRAMMAR.get(domain, DOMAIN_GRAMMAR["general"])
    return {
        "system": SYSTEM_ID, "plan_id": f"msc-{digest}", "format": fmt,
        "domain": domain, "duration": round(duration, 3),
        "truth_boundary": (
            "Public works support observable craft analysis; this plan never claims an internal LUT, "
            "preset, timeline, transition pack or frame-identical reproduction."
        ),
        "shot_grammar": list(grammar),
        "camera": {
            "rule": "movement follows subject, space or reveal; no decorative digital drift",
            "coverage": ["context_wide", "action_medium", "evidence_detail", "reaction_or_consequence"],
            "continuity": ["screen_direction", "eyeline", "action_peak", "subject_anchor"],
        },
        "editing": {
            "default": "clean_cut", "expressive_limit": expressive_limit,
            "expressive_used": expressive_used, "transitions": transitions,
            "rhythm": "compress setup, vary shot length, insert one readable breath before payoff",
        },
        "sound": {
            "priority": ["dialogue_or_sync", "production_sound", "room_tone", "specific_foley", "music"],
            "bridges": ["j_cut", "l_cut", "wild_track_continuity"],
            "payoff": "reduce music before the reveal; land sync sound, impact or intentional silence",
            "block": "generic whoosh on every cut",
        },
        "colour": {
            "pipeline": ["input_transform", "exposure_white_balance", "shot_match", "look", "output_transform"],
            "rule": "source and shot matching first; one restrained look, scopes and skin/object truth preserved",
            "block": "hard-stacked LUT or saturation used to fake cinematic footage",
        },
        "graphics_vfx": {
            "roles": ["explain_hidden_process", "show_scale", "locate_attention", "prove_measurement"],
            "rule": "graphics inherit camera perspective and lighting when spatial; otherwise remain quiet editorial overlays",
            "block": "full-screen generic cards, grid openers, transition packs or effects without information value",
        },
        "qa": {
            "required": ["cut_motivation", "continuity", "audio_bridge", "shot_match", "payoff_hold"],
            "frame_checks": ["no_flash_frame", "no_mask_leak", "no_subject_crop", "no_label_leak"],
            "human_review": "Hao timestamp review remains mandatory",
        },
    }


def apply_transition_decisions(sequence_plan: list[dict[str, Any]], craft_plan: dict[str, Any]) -> list[dict[str, Any]]:
    decisions = (craft_plan.get("editing") or {}).get("transitions") or []
    output = []
    for index, source in enumerate(sequence_plan or []):
        row = dict(source)
        if index < len(decisions):
            row["transition_requested"] = decisions[index]["requested"]
            row["transition_out"] = decisions[index]["selected"]
            row["transition_status"] = decisions[index]["status"]
            row["transition_missing"] = decisions[index]["missing"]
        output.append(row)
    return output


def validate_craft_plan(plan: dict[str, Any]) -> list[str]:
    bad: list[str] = []
    if plan.get("system") != SYSTEM_ID:
        bad.append("wrong system id")
    edit = plan.get("editing") or {}
    decisions = edit.get("transitions") or []
    if sum(row.get("selected") != "clean_cut" for row in decisions) > int(edit.get("expressive_limit", 0)):
        bad.append("expressive transition budget exceeded")
    if any(row.get("status") == "READY" and row.get("missing") for row in decisions):
        bad.append("transition marked READY with missing evidence")
    if any(row.get("selected") not in TRANSITION_CONTRACTS for row in decisions):
        bad.append("unknown selected transition")
    if not (plan.get("sound") or {}).get("priority") or not (plan.get("colour") or {}).get("pipeline"):
        bad.append("incomplete sound or colour pipeline")
    if not plan.get("truth_boundary"):
        bad.append("missing truth boundary")
    return bad


def _self_test() -> None:
    seq = [
        {"act": "hook", "end": 2.0, "transition_out": "match_cut"},
        {"act": "context", "end": 7.0, "transition_out": "speed_ramp"},
        {"act": "payoff", "end": 14.0, "transition_out": "audio_bridge"},
    ]
    empty = compile_craft_plan(duration=18, format="short", domain="toy", sequence_plan=seq)
    assert not validate_craft_plan(empty)
    assert all(row["selected"] == "clean_cut" for row in empty["editing"]["transitions"])
    ready = compile_craft_plan(
        duration=60, format="longform", domain="product", sequence_plan=seq,
        evidence={"matched_subject_anchor", "matched_scale_or_shape", "semantic_relation",
                  "high_fps_source", "motion_peak", "ramp_preserves_subject_readability",
                  "incoming_audio_clean", "dialogue_or_ambient_motivates_next_scene"},
    )
    assert not validate_craft_plan(ready)
    assert ready["editing"]["expressive_used"] <= ready["editing"]["expressive_limit"]
    applied = apply_transition_decisions(seq, empty)
    assert applied[0]["transition_requested"] == "match_cut"
    assert applied[0]["transition_out"] == "clean_cut"
    print("mediastorm_craft self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("selftest", "knowledge"))
    args = parser.parse_args(argv)
    if args.command == "selftest":
        _self_test()
    else:
        print(json.dumps(json.loads(KNOWLEDGE.read_text(encoding="utf-8")), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
