# -*- coding: utf-8 -*-
"""Evidence-bound shot style guidance for human and Editkin v4 planning.

The source reference is a privately supplied filmmaker document. These are
original, condensed decision tags rather than a redistribution of that text.
No frame, performance, or right is inferred from a style name.
"""
from __future__ import annotations

from typing import Any


STYLE_GUIDES: dict[str, dict[str, Any]] = {
    "realist": {"label": "寫實", "focus": ["continuous_action", "unposed_reaction", "location_sound", "natural_light", "observer_camera"], "avoid": ["staged_reaction", "unmotivated_camera_move"], "exception": "紀實訪談可直接看鏡頭；保留真實對話。"},
    "stylized": {"label": "風格化／藝術化", "focus": ["designed_composition", "intentional_color", "symbolic_action", "visual_pause", "controlled_motion"], "avoid": ["unmotivated_effect", "decorative_only"], "exception": "構圖不能取代情節或事實證據。"},
    "suspense_horror": {"label": "懸疑／恐怖", "focus": ["concealment", "delayed_reaction", "sound_tension", "reveal_handle", "negative_space"], "avoid": ["premature_reveal", "unmotivated_scare"], "exception": "暗畫面要有角色、事件或聲音承接。"},
    "action_adventure": {"label": "動作／冒險", "focus": ["clear_action", "readable_direction", "spatial_context", "matching_motion", "reaction_timing"], "avoid": ["unreadable_blur", "incoherent_space"], "exception": "快剪仍須保留動作方向和因果。"},
    "romance": {"label": "浪漫／愛情", "focus": ["reciprocal_glance", "mutual_reaction", "small_gesture", "soft_light", "proximity_change"], "avoid": ["one_sided_reaction", "staged_contact"], "exception": "單人反應不能證明雙方關係。"},
    "sci_fi_fantasy": {"label": "科幻／奇幻", "focus": ["world_rule_evidence", "character_response", "world_scale", "motivated_light", "spatial_exploration"], "avoid": ["generic_glow", "effect_without_world_rule"], "exception": "特效需讓世界規則可理解，虛構不得冒充紀實。"},
    "character_drama": {"label": "人物強敘事", "focus": ["decision_moment", "before_after_behavior", "relationship_shift", "reaction_context", "setting_change"], "avoid": ["isolated_expression", "unearned_emotion"], "exception": "表情沒有前後脈絡時不能宣稱角色弧線。"},
    "vlog": {"label": "Vlog", "focus": ["first_person_interaction", "everyday_action", "voice_reaction_sync", "natural_imperfection", "life_transition"], "avoid": ["staged_everyday", "inaudible_speech"], "exception": "手持現場感可用，但不能犧牲內容可辨識度。"},
    "commercial_ad": {"label": "商業廣告", "focus": ["demonstrated_use", "problem_solution", "product_visible", "verified_change", "single_cta"], "avoid": ["unverified_claim", "logo_only"], "exception": "產品功效與前後對比必須有可核對來源。"},
}


def shot_selection_policy(style_id: str = "auto") -> dict[str, Any]:
    """Return a compact routing policy; auto cannot silently pick a style."""
    if style_id == "auto":
        return {"status": "STYLE_CHOICE_REQUIRED", "style_id": None,
                "available_styles": list(STYLE_GUIDES), "selected_shots": [],
                "rule": "依本片敘事目的選風格；逐鏡檢查畫面、聲音、權利和時間碼。"}
    if style_id not in STYLE_GUIDES:
        raise ValueError(f"unknown shot style: {style_id}")
    guide = STYLE_GUIDES[style_id]
    return {"status": "AWAITING_SHOT_EVIDENCE", "style_id": style_id,
            "focus": guide["focus"], "avoid": guide["avoid"],
            "exception": guide["exception"], "selected_shots": [],
            "rule": "僅以已核對的來源鏡頭與聲音排序；排行是待審建議，不得直接執行剪輯。"}


def rank_shot_candidates(style_id: str, candidates: list[dict]) -> dict[str, Any]:
    """Score reviewer-annotated candidates; this function performs no media analysis."""
    if style_id not in STYLE_GUIDES:
        raise ValueError(f"unknown shot style: {style_id}")
    if len(candidates) > 128 or len({row.get("id") for row in candidates}) != len(candidates):
        raise ValueError("too many or duplicate shot candidates")
    guide = STYLE_GUIDES[style_id]
    rows = []
    for row in candidates:
        candidate_id = str(row.get("id") or "")
        if not candidate_id or not row.get("source_ref") or not row.get("rights_approved") or not row.get("beat_purpose_matched"):
            rows.append({"id": candidate_id, "status": "BLOCKED", "points": None})
            continue
        observations = row.get("observations") or []
        if not observations or any(not item.get("evidence_ref") for item in observations):
            rows.append({"id": candidate_id, "status": "REVIEW_REQUIRED", "points": None})
            continue
        observed = {item.get("signal") for item in observations}
        positive = [signal for signal in guide["focus"] if signal in observed]
        if not positive:
            rows.append({"id": candidate_id, "status": "REVIEW_REQUIRED", "points": None})
            continue
        negative = [signal for signal in guide["avoid"] if signal in observed]
        # This ordinal score is a triage aid, not a probability or aesthetic grade.
        points = max(0, sum(2 if index < 3 else 1 for index, signal in enumerate(guide["focus"]) if signal in observed) - 2 * len(negative))
        rows.append({"id": candidate_id, "status": "DRAFT_RANKING_REVIEW_REQUIRED",
                     "points": points, "matched": positive, "counterevidence": negative})
    rows.sort(key=lambda item: (-(item["points"] if item["points"] is not None else -1), item["id"]))
    return {"style_id": style_id, "evidence_authority": "caller_asserted_unverified",
            "direct_apply_allowed": False, "rows": rows}


def _self_test() -> None:
    assert len(STYLE_GUIDES) == 9
    assert shot_selection_policy()["status"] == "STYLE_CHOICE_REQUIRED"
    assert shot_selection_policy("vlog")["selected_shots"] == []
    result = rank_shot_candidates("vlog", [
        {"id": "daily", "source_ref": "clip:00:10", "rights_approved": True, "beat_purpose_matched": True,
         "observations": [{"signal": "first_person_interaction", "evidence_ref": "frame:300"}]},
        {"id": "unknown-rights", "source_ref": "clip:00:20", "rights_approved": False, "beat_purpose_matched": True,
         "observations": [{"signal": "everyday_action", "evidence_ref": "frame:600"}]},
    ])
    assert result["rows"][0]["id"] == "daily" and result["rows"][0]["points"] == 2
    assert result["rows"][1]["status"] == "BLOCKED" and not result["direct_apply_allowed"]
    try:
        shot_selection_policy("invented")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown style must fail")


if __name__ == "__main__":
    _self_test()
    print("shot_selection_language self-test OK")
