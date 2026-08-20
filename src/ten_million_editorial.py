# -*- coding: utf-8 -*-
"""Compile MrBeast information craft and 影視颶風 filmmaking craft into one gate.

"Ten-million" is an internal quality target, never a view guarantee.  The
compiler combines two independently evidence-gated planners and keeps the
result diagnostic until the frozen editorial-parity blind benchmark passes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mediastorm_craft import apply_transition_decisions, compile_craft_plan, validate_craft_plan
from mrbeast_editing_system import plan_sequence, validate_plan


SYSTEM_ID = "hao-ten-million-editorial-v1"
BENCHMARK_ID = "editorial-parity-v1"
ROOT = Path(__file__).resolve().parent

SCORE_AXES = {
    "opening_promise": "開場立刻說清衝突、規模或結果",
    "progression_and_stakes": "進度、限制與勝負持續可見",
    "information_energy": "數字、標示與視覺事件只服務理解",
    "payoff_and_proof": "高潮有證據、有停留、有聲畫落點",
    "shot_motivation": "鏡頭運動與景別服務主體、空間或揭露",
    "continuity": "方向、動作、視線與空間連續",
    "sound_architecture": "同步聲、環境、J/L-cut、音樂與靜默有層次",
    "colour_and_match": "先校正與 shot match，再施加克制 look",
    "vfx_integration": "Tracking、遮罩、3D、VFX 具透視、光線與逐幀證據",
    "restraint_and_breath": "刺激與呼吸形成對比，不靠每剪必特效",
}

CONFLICT_PRIORITY = [
    "truth_and_provenance",
    "premise_clarity",
    "story_and_subject",
    "continuity_and_audio",
    "visual_polish",
]


def compile_ten_million_plan(*, duration: float, format: str, domain: str,
                             beats: list[dict[str, Any]],
                             sequence_plan: list[dict[str, Any]],
                             evidence: list[str] | set[str] | None = None,
                             seed: object = 0) -> dict[str, Any]:
    high_information = plan_sequence(beats, format=format)
    cinematic = compile_craft_plan(
        duration=duration, format=format, domain=domain,
        sequence_plan=sequence_plan, evidence=evidence, seed=seed,
    )
    resolved_sequence = apply_transition_decisions(sequence_plan, cinematic)
    return {
        "schema_version": 1,
        "system": SYSTEM_ID,
        "benchmark_id": BENCHMARK_ID,
        "quality_target": "ten_million_editorial",
        "view_guarantee": False,
        "format": cinematic["format"],
        "domain": domain,
        "duration": float(duration),
        "pillars": {
            "mrbeast_information_craft": high_information,
            "mediastorm_cinematic_craft": cinematic,
        },
        "resolved_sequence": resolved_sequence,
        "score_axes": SCORE_AXES,
        "conflict_priority": CONFLICT_PRIORITY,
        "promotion": {
            "status": "DIAGNOSTIC",
            "requires": [
                "frozen_24_project_dataset",
                "blind_holdout_pairwise_preference_at_least_0.45",
                "minimum_domain_preference_at_least_0.35",
                "zero_critical_visual_regressions",
                "hao_timestamp_review",
            ],
            "rule": "Neither benchmark may pass by prose; selected effects and transitions need shot-level evidence.",
        },
    }


def validate_ten_million_plan(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if plan.get("system") != SYSTEM_ID:
        errors.append("wrong system id")
    pillars = plan.get("pillars") or {}
    mrbeast = pillars.get("mrbeast_information_craft") or {}
    mediastorm = pillars.get("mediastorm_cinematic_craft") or {}
    errors.extend("mrbeast: " + item for item in validate_plan(mrbeast))
    errors.extend("mediastorm: " + item for item in validate_craft_plan(mediastorm))
    if set(plan.get("score_axes") or {}) != set(SCORE_AXES):
        errors.append("ten-axis scorecard is incomplete")
    if plan.get("view_guarantee") is not False:
        errors.append("quality target must not claim guaranteed views")
    if (plan.get("promotion") or {}).get("status") != "DIAGNOSTIC":
        errors.append("plan cannot self-promote before blind benchmark and Hao review")
    if not mrbeast or not mediastorm:
        errors.append("both benchmark pillars are mandatory")
    return errors


def self_test() -> None:
    beats = [
        {"time": 0, "event": "promise_cold_open", "evidence": ["real_payoff_or_conflict_shot"]},
        {"time": 2, "event": "proof_freeze", "evidence": ["proof_frame", "source_id"]},
    ]
    sequence = [
        {"act": "hook", "end": 2.0, "transition_out": "match_cut"},
        {"act": "proof", "end": 6.0, "transition_out": "clean_cut"},
    ]
    plan = compile_ten_million_plan(
        duration=8, format="shorts", domain="toy", beats=beats,
        sequence_plan=sequence, evidence=set(), seed="fixture",
    )
    assert not validate_ten_million_plan(plan), validate_ten_million_plan(plan)
    assert plan["resolved_sequence"][0]["transition_out"] == "clean_cut"
    assert plan["view_guarantee"] is False
    assert len(plan["score_axes"]) == 10
    print("ten_million_editorial self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile the Hao ten-million editorial dual benchmark")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest")
    plan_parser = sub.add_parser("plan")
    plan_parser.add_argument("input", help="JSON containing duration, format, domain, beats and sequence_plan")
    plan_parser.add_argument("--output")
    args = parser.parse_args(argv)
    if args.command == "selftest":
        self_test()
        return 0
    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    plan = compile_ten_million_plan(
        duration=source["duration"], format=source["format"], domain=source["domain"],
        beats=source.get("beats") or [], sequence_plan=source.get("sequence_plan") or [],
        evidence=source.get("evidence") or [], seed=source.get("seed", 0),
    )
    plan["errors"] = validate_ten_million_plan(plan)
    payload = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 1 if plan["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
