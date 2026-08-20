# -*- coding: utf-8 -*-
"""Fail-closed BEYBLADE X finish validator.

This module does not pretend that a single frame can judge a battle.  It
validates structured, sequence-level evidence before an official Finish label
is allowed into a public render.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


RULES_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "runtime" / "beyblade_x_rules.json"
FINISH_ALIASES = {
    "xtreme": "xtreme",
    "extreme": "xtreme",
    "xtreme finish": "xtreme",
    "extreme finish": "xtreme",
    "over": "over",
    "over finish": "over",
    "knock out": "over",
    "knock out finish": "over",
    "burst": "burst",
    "burst finish": "burst",
    "spin": "spin",
    "spin finish": "spin",
    "survivor": "spin",
    "survivor finish": "spin",
    "draw": "draw",
    "draw / replay": "draw",
    "replay": "draw",
}


def load_rules(path: str | Path = RULES_PATH) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not data.get("finish_types"):
        raise ValueError(f"Invalid BEYBLADE X rules file: {path}")
    return data


def normalize_finish(value: Any) -> str:
    key = re.sub(r"\s+", " ", str(value or "").strip().lower())
    return FINISH_ALIASES.get(key, key)


def score_label(finish: Any, *, rules: dict[str, Any] | None = None) -> str:
    rules = rules or load_rules()
    key = normalize_finish(finish)
    row = rules["finish_types"].get(key)
    if not row:
        raise ValueError(f"Unknown Finish: {finish!r}")
    points = int(row["points"])
    return row["display"] if points == 0 else f'{row["display"]} +{points}'


def visible_finish(text: str) -> str | None:
    """Return the canonical finish explicitly named in public-facing text."""
    upper = str(text or "").upper()
    patterns = (
        ("xtreme", r"\b(?:XTREME|EXTREME)\s+FINISH\b"),
        ("over", r"\b(?:OVER|KNOCK\s*OUT)\s+FINISH\b"),
        ("burst", r"\bBURST\s+FINISH\b"),
        ("spin", r"\b(?:SPIN|SURVIVOR)\s+FINISH\b"),
        ("draw", r"\bDRAW\b|\bREPLAY\b"),
    )
    found = [key for key, pattern in patterns if re.search(pattern, upper)]
    return found[0] if len(found) == 1 else ("multiple" if found else None)


def _matchup_identity(matchup: dict[str, Any] | None) -> tuple[list[str], list[str]]:
    names: list[str] = []
    authenticity: list[str] = []
    if isinstance(matchup, dict):
        for side in ("left", "right"):
            row = matchup.get(side) or {}
            names.append(str(row.get("name", "")).strip())
            authenticity.append(str(row.get("authenticity", "")).strip())
    return names, authenticity


def _parse_confidence(evidence: dict[str, Any], failures: list[str]) -> float:
    try:
        confidence = float(evidence.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
        failures.append("evidence.confidence 必須是 0..1 數值")
    if not 0.0 <= confidence <= 1.0:
        failures.append("evidence.confidence 必須介於 0 與 1")
    return confidence


def _validate_event_order(finish: str, evidence: dict[str, Any],
                          failures: list[str]) -> str:
    simultaneous = bool(evidence.get("simultaneous"))
    unjudgeable = bool(evidence.get("unjudgeable"))
    first_event = normalize_finish(evidence.get("first_event"))
    if finish == "draw":
        if not (simultaneous or unjudgeable or evidence.get("judge_replay")):
            failures.append("DRAW / REPLAY 必須有同時發生、無法判定或裁判重賽證據")
    else:
        if simultaneous or unjudgeable:
            failures.append("同時發生或無法判定時不可硬貼 Finish，應改 DRAW / REPLAY")
        if not first_event:
            failures.append("非和局必須標記 first_event，才能確認最先成立的 Finish")
        elif first_event != finish:
            failures.append(f"最先發生的是 {first_event}，不可標成 {finish}")
    return first_event


def _validate_finish_evidence(finish: str, first_event: str,
                              evidence: dict[str, Any], failures: list[str]) -> None:
    if finish in {"xtreme", "over"}:
        if not evidence.get("whole_body_entered"):
            failures.append(f"{finish} 必須確認對手整顆進入判定區")
        if str(evidence.get("opponent_zone", "")).lower() != finish:
            failures.append(f"{finish} 必須有 opponent_zone={finish}")
        if evidence.get("returned_to_battle_zone") is not False:
            failures.append(f"{finish} 必須明確確認沒有旋轉著回到 Battle Zone")
    elif finish == "burst":
        if not evidence.get("opponent_parts_separated"):
            failures.append("Burst Finish 必須看見對手零件脫落並分離")
        if first_event != "burst":
            failures.append("Burst Finish 必須確認零件分離是最先發生的 Finish 瞬間")
        if evidence.get("grip_bit_only"):
            failures.append("僅 Battle Grip 的 Grip Bit 脫離不算 Burst Finish")
    elif finish == "spin":
        if not evidence.get("opponent_rotation_zero"):
            failures.append("Spin Finish 必須確認對手原旋轉方向速度先歸零")
        if not evidence.get("winner_rotation_positive"):
            failures.append("Spin Finish 必須確認勝方當下仍在旋轉")
        if str(evidence.get("opponent_zone", "")).lower() != "battle":
            failures.append("Spin Finish 的停止判定必須發生在 Battle Zone")
        if first_event != "spin":
            failures.append("Spin Finish 必須是最先發生的 Finish 瞬間")


def _validate_review_confidence(result: dict[str, Any], confidence: float,
                                rules: dict[str, Any], failures: list[str]) -> None:
    min_review = float(rules["editing_policy"]["minimum_review_confidence"])
    min_auto = float(rules["editing_policy"]["minimum_auto_confidence"])
    if confidence < min_review:
        failures.append(f"判定信心 {confidence:.2f} 低於審核門檻 {min_review:.2f}")
    elif not result.get("human_verified") and confidence < min_auto:
        failures.append(
            f"未經創作者確認時，公開 Finish 標籤需 confidence>={min_auto:.2f}；目前 {confidence:.2f}"
        )


def _validate_visible_label(finish: str, visible_text: str, rules: dict[str, Any],
                            failures: list[str], warnings: list[str]) -> None:
    shown = visible_finish(visible_text)
    if shown == "multiple":
        failures.append("同一結果畫面混用了多套 Finish 名稱")
    elif shown and shown != finish:
        failures.append(f"畫面標籤是 {shown}，但 battle_result 是 {finish}")
    elif visible_text and not shown:
        warnings.append(f"結果已確認，建議使用官方計分標籤：{score_label(finish, rules=rules)}")


def validate_battle_result(
    result: Any,
    *,
    matchup: dict[str, Any] | None = None,
    visible_text: str = "",
    rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a proposed result against official, sequence-level evidence.

    Public labels are GREEN only after frame-sequence review and either human
    confirmation or exceptionally clear (>=0.97) structured evidence.
    """
    rules = rules or load_rules()
    failures: list[str] = []
    warnings: list[str] = []
    if not isinstance(result, dict):
        return {"status": "BLOCKED", "failures": ["battle_result 必須是 dict"], "warnings": []}

    finish = normalize_finish(result.get("finish"))
    if finish not in rules["finish_types"]:
        return {
            "status": "BLOCKED",
            "failures": ["finish 僅可為 xtreme/over/burst/spin/draw"],
            "warnings": [],
        }

    winner = str(result.get("winner", "")).strip()
    evidence = result.get("evidence") or {}
    if not isinstance(evidence, dict):
        failures.append("battle_result.evidence 必須是 dict")
        evidence = {}

    names, authenticity = _matchup_identity(matchup)
    if finish != "draw":
        if not winner:
            failures.append("非和局必須提供 winner")
        elif names and winner not in names:
            failures.append(f"winner={winner!r} 不在 battle_matchup 參賽者中")

    confidence = _parse_confidence(evidence, failures)
    if not evidence.get("sequence_reviewed"):
        failures.append("必須逐格／慢動作檢查完整事件順序，不能看單張畫面猜 Finish")

    first_event = _validate_event_order(finish, evidence, failures)
    _validate_finish_evidence(finish, first_event, evidence, failures)
    _validate_review_confidence(result, confidence, rules, failures)
    _validate_visible_label(finish, visible_text, rules, failures, warnings)

    if "counterfeit" in authenticity:
        warnings.append("此為含盜版陀螺的趣味對戰；文案須註明非官方賽事判定")

    return {
        "status": "GREEN" if not failures else "BLOCKED",
        "finish": finish,
        "winner": winner or None,
        "label": score_label(finish, rules=rules),
        "points": int(rules["finish_types"][finish]["points"]),
        "failures": failures,
        "warnings": warnings,
    }


def selftest() -> None:
    matchup = {
        "left": {"name": "榮耀女武神", "authenticity": "official"},
        "right": {"name": "黃金神杖", "authenticity": "counterfeit"},
    }
    burst = {
        "finish": "burst",
        "winner": "榮耀女武神",
        "human_verified": True,
        "evidence": {
            "sequence_reviewed": True,
            "confidence": 0.95,
            "first_event": "burst",
            "opponent_parts_separated": True,
            "simultaneous": False,
        },
    }
    good = validate_battle_result(
        burst, matchup=matchup, visible_text="BURST FINISH +2"
    )
    assert good["status"] == "GREEN" and good["points"] == 2
    false_burst = json.loads(json.dumps(burst, ensure_ascii=False))
    false_burst["evidence"]["opponent_parts_separated"] = False
    assert validate_battle_result(false_burst, matchup=matchup)["status"] == "BLOCKED"
    returned = {
        "finish": "over",
        "winner": "榮耀女武神",
        "human_verified": True,
        "evidence": {
            "sequence_reviewed": True,
            "confidence": 0.99,
            "first_event": "over",
            "whole_body_entered": True,
            "opponent_zone": "over",
            "returned_to_battle_zone": True,
        },
    }
    assert validate_battle_result(returned, matchup=matchup)["status"] == "BLOCKED"
    simultaneous = json.loads(json.dumps(burst, ensure_ascii=False))
    simultaneous["evidence"]["simultaneous"] = True
    assert validate_battle_result(simultaneous, matchup=matchup)["status"] == "BLOCKED"
    draw = {
        "finish": "draw",
        "evidence": {
            "sequence_reviewed": True,
            "confidence": 1.0,
            "simultaneous": True,
        },
    }
    assert validate_battle_result(draw, matchup=matchup)["status"] == "GREEN"
    print("beyblade_x_rules selftest: PASS")


if __name__ == "__main__":
    selftest()
