"""Original CSS method learning and frame-evidenced art scores, never image inference.

The six methods are a self-authored study. Export availability is deliberately
false until a current renderer and complete artifact prove it. Scores explain
the authorized reviewer's actual observations; they never replace that review.
"""
from __future__ import annotations

import math
import re
from agent_art_review import DIMENSIONS, validate_agent_review

NATIVE_REFERENCE_TEMPLATE_IDS = (
    "strike_reframe", "level_bridge", "comparison_pair", "context_stack",
    "evidence_takeover", "focus_wall", "brand_recap", "kinetic_network",
)


def compile_native_graphic_direction(raw, *, format="shorts"):
    """Owned native authoring input, never a CSS exporter or rendered approval."""
    if not isinstance(format, str) or format not in {
            "longform", "shorts", "reels", "vlog", "podcast", "interview", "ai_short_drama"}:
        raise ValueError("native graphic direction requires a supported format")
    if format in {"longform", "podcast", "interview"}:
        raise ValueError("whole-board native template direction is unavailable for continuous longform UI and narration")
    if not isinstance(raw, dict) or set(raw) != {"templateId", "graphicCadence", "style"}:
        raise ValueError("native graphic direction requires only templateId, graphicCadence and complete style")
    template, cadence = raw["templateId"], raw["graphicCadence"]
    if not isinstance(template, str) or template not in NATIVE_REFERENCE_TEMPLATE_IDS:
        raise ValueError("unknown native reference template")
    if not isinstance(cadence, str) or cadence not in {"legacy", "brisk", "kinetic"}:
        raise ValueError("unknown native graphic cadence")
    style = raw["style"]
    if (not isinstance(style, dict) or set(style) - {"palette", "typography", "animationSpeed"}
            or not {"palette", "typography"}.issubset(style)):
        raise ValueError("native graphic direction requires complete palette, typography and animationSpeed")
    palette, typography, speed = style["palette"], style["typography"], style.get("animationSpeed", 1)
    palette_keys = {"surface", "text", "accent", "muted", "separator"}
    if (not isinstance(palette, dict) or set(palette) != palette_keys
            or any(not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value)
                   for value in palette.values())):
        raise ValueError("native palette requires exactly five six-digit RGB colors")
    if not isinstance(typography, dict) or set(typography) != {"headingFamily", "bodyFamily"}:
        raise ValueError("native typography requires headingFamily and bodyFamily")
    if any(not isinstance(value, str) or len(value.strip()) > 80 or not value.strip()
           for value in typography.values()):
        raise ValueError("native font families must be bounded nonempty text; actual font bytes remain required")
    if type(speed) not in (int, float) or not .5 <= speed <= 2 or not math.isfinite(speed):
        raise ValueError("native animationSpeed must be a finite non-boolean number from .5 to 2")

    def luminance(color):
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4 for value in channels]
        return linear[0] * .2126 + linear[1] * .7152 + linear[2] * .0722

    def contrast(left, right):
        a, b = luminance(left), luminance(right)
        return (max(a, b) + .05) / (min(a, b) + .05)

    if contrast(palette["surface"], palette["text"]) < 4.5 or contrast(palette["surface"], palette["muted"]) < 3:
        raise ValueError("native palette needs text contrast >=4.5 and muted contrast >=3 against surface")
    return {"templateId": template, "graphicCadence": cadence,
            "style": {"palette": dict(palette),
                      "typography": {key: value.strip() for key, value in typography.items()},
                      "animationSpeed": speed}}

METHODS = (
    {"id": "chat", "purpose": "question_answer", "motion": "local_settle_then_character_reveal", "requires": ["actual_question_and_answer", "physical_glyph_coverage", "reading_hold"]},
    {"id": "quest", "purpose": "process_detail", "motion": "stable_header_expand_then_details", "requires": ["verified_steps", "stable_element_identity", "reading_hold"]},
    {"id": "score", "purpose": "verified_milestone", "motion": "staggered_split_flap_digit_change", "requires": ["verified_number_and_units", "actual_previous_and_next_value", "bounded_hinge_renderer"]},
    {"id": "tap", "purpose": "local_attention", "motion": "short_local_rings_then_clear", "requires": ["observed_ui_coordinate", "actual_operation_time", "unobscured_proof"]},
    {"id": "rarity", "purpose": "earned_payoff", "motion": "brief_ornament_then_readable_settle", "requires": ["actual_achievement", "one_subject", "quiet_hold"]},
    {"id": "wipe", "purpose": "motivated_handoff", "motion": "six_sided_cover_then_second_scene", "requires": ["two_actual_scenes", "semantic_reason", "explicit_handoff_frame"]},
)
QUESTIONS = (
    "真實字型、字重和斷行是否與輸出一致？", "文字與真UI是否讀得完？",
    "當下唯一焦點和視線交接是否清楚？", "自有品牌配色及實際背景對比是否適合？",
    "留白、對齊、字幕與操作區是否互不擠壓？", "畫面是否逐句支持本人說法及真來源？",
    "提示是否遮擋主體、操作或證據？", "柔邊、陰影和素材輪廓是否自然？",
    "動作、切點及停留是否服務語意並保留來源時鐘？", "段落是否連續、完整而有收束？",
)


def quality_rubric(format="longform"):
    if format not in {"longform", "shorts"}:
        raise ValueError("quality format must be longform or shorts")
    weights = (10, 16, 12, 8, 6, 20, 8, 5, 8, 7) if format == "longform" else (12, 14, 14, 9, 7, 14, 9, 6, 9, 6)
    return {"schema": "video-autopilot.frame-evidenced-art-rubric/v1", "format": format,
            "dimensions": [{"id": name, "weight": weight, "question": question}
                           for name, weight, question in zip(DIMENSIONS, weights, QUESTIONS)],
            "ratingRange": [0, 5], "aggregation": "worst_observation_per_dimension",
            "minimumDimensionRating": 3.5, "targetScore": 90,
            "requires": ["same_artifact_full_decode", "continuous_motion_observation", "frame_ranges_and_specific_findings", "authorized_reviewer"],
            "boundary": "explanatory observed-art score; not automated image understanding, completion percent, forecast or publication readiness"}


def compile_learning_plan(request):
    format = "longform" if request.get("format") in {"longform", "podcast", "interview"} else "shorts"
    # Longform extracts only useful local attention. Never insert a whole gallery,
    # decorative score, bubble, chapter board or a replacement fake product UI.
    selected = [row for row in METHODS if format != "longform" or row["id"] == "tap"]
    return {"schema": "video-autopilot.original-css-method-learning/v1",
            "provenance": {"kind": "self_authored_css_study", "study": "yui-game-css-20261001",
                           "cssSha256": "65bd26ea369103cc8092a423ce93dfccdebacbd20e64418acdfbaaddb27a871a",
                           "javascriptSha256": "9a40b81f4e62d369d7f2f1846a5a093ea312ef5785b5aaa1e32e2d8180c714cf",
                           "referenceRole": "methods_only_not_imported_media_or_ui"},
            "methods": [{**row, "exportReady": False, "availability": "DESIGN_STUDY_NOT_EXPORT_VERIFIED"} for row in selected],
            "omittedMethods": [row["id"] for row in METHODS if row not in selected],
            "paletteRoles": ["primary", "background", "ink", "grid"],
            "nativeGraphicCadence": {"directionField": "beats[].nativeTemplateDirection",
                                     "profileField": "graphicCadence", "profiles": ["legacy", "brisk", "kinetic"], "newAuthoringDefault": "kinetic",
                                     "profileContract": "editkin.graphic-cadence/v1",
                                     "consumer": "prepare_reference_motion_template",
                                     "availability": "PARTIAL_NATIVE_AUTHORING_REQUIRES_CURRENT_V4_AND_ARTIFACT_REVIEW",
                                     "scope": "native graphic cadence and explicit palette; preserve media clocks, audio and narration",
                                     "longform": "no whole-board nativeTemplateDirection; actual local hints need observed UI and physical glyphs",
                                     "cssExportReady": False, "certified": False},
            "clock": "explicit_project_frames_and_stable_element_ids_not_wall_clock_css_loop",
            "typography": "actual_full_physical_glyphs_required; study_subset338_codepoints_is_not_general_TC_support",
            "fallback": "clean_hold_or_already_verified_native_semantic_hint; never_execute_unverified_css_as_current_film",
            "longformRule": "full_size_real_ui_continuous_narration_sparse_local_hint_no_gallery_or_PPT",
            "qualityRubric": quality_rubric(format), "reviewRequired": True, "certified": False}


def score_visual_findings(review, policy, *, format="longform"):
    rubric = quality_rubric(format)
    checked = validate_agent_review(review, policy)
    observations = review.get("observations") or []
    errors, rows = [], []
    earned = 0.0
    for axis in rubric["dimensions"]:
        candidates = [row for row in observations if isinstance(row, dict) and row.get("dimension") == axis["id"]]
        ratings = [row.get("rating") for row in candidates]
        valid = bool(ratings) and all(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 5 for value in ratings)
        rating = min(ratings) if valid else None
        if not valid:
            errors.append("missing or invalid observed rating: " + axis["id"])
        points = rating / 5 * axis["weight"] if rating is not None else None
        if points is not None:
            earned += points
        rows.append({**axis, "rating": rating, "points": points,
                     "findings": [{"startFrame": row.get("startFrame"), "endFrame": row.get("endFrame"),
                                   "verdict": row.get("verdict"), "detail": row.get("detail")} for row in candidates]})
    score = round(earned, 1) if not errors else None
    status = "BLOCKED" if checked["status"] == "BLOCKED" else "REVIEW"
    if (checked["completed"] and not errors and score is not None and score >= rubric["targetScore"]
            and all(row["rating"] >= rubric["minimumDimensionRating"] for row in rows)):
        status = "PASSED"
    return {"schema": "video-autopilot.frame-evidenced-art-score/v1", "status": status,
            "score": score, "dimensions": rows, "errors": checked["errors"] + errors,
            "reviewer": "agent", "outputSha256": checked["outputSha256"],
            "visualReviewCompleted": checked["completed"], "certified": False,
            "publicationReady": False, "rule": rubric["boundary"]}
