"""Public workflow component (public distribution).

Configurable workflow component; public fixtures carry no creator data or live proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

from art_direction import THEMES
from asset_registry import PLAN_NAME as ASSET_PLAN_NAME
from camera_transition_director import validate_shot_dynamics_system
from caption_director import validate_caption_system
from context_router import PACKET_NAME
from editorial_templates import STYLES as EDITORIAL_STYLES
from visual_plan_support import PROFILES


def _validate_events(events: list[dict], duration: float) -> list[str]:
    bad, last_card, glitch_count, last_end = [], None, 0, -1.0
    for event in events:
        start, event_duration = float(event["t"]), float(event["duration"])
        if start < 0 or start + event_duration > duration + .05:
            bad.append("event outside duration @%.2f" % start)
        if start < last_end - .05:
            bad.append("events overlap @%.2f" % start)
        if event.get("card") == last_card and event.get("type") == "pattern_interrupt":
            bad.append("same card repeated: %s" % last_card)
        if "glitch" in str(event.get("transition")):
            glitch_count += 1
        last_card, last_end = event.get("card"), start + event_duration
    if glitch_count > 1:
        bad.append("glitch used more than once")
    return bad


def _validate_energy_curve(curve: list[dict], duration: float) -> list[str]:
    if not curve:
        return ["missing energy curve"]
    bad, cursor = [], 0.0
    for act in curve:
        if abs(float(act["start"]) - cursor) > .01:
            bad.append("energy curve gap @%.2f" % cursor)
        if not 0 <= float(act["energy"]) <= 1:
            bad.append("energy outside 0..1")
        cursor = float(act["end"])
    if abs(cursor - duration) > .02:
        bad.append("energy curve does not end at duration")
    named = {act["name"]: act for act in curve}
    if "breath" not in named or "payoff" not in named:
        bad.append("missing breath/payoff")
    elif float(named["payoff"]["energy"]) <= float(named["breath"]["energy"]):
        bad.append("payoff must exceed breath energy")
    elif abs(float(named["breath"]["end"]) - float(named["payoff"]["start"])) > .02:
        bad.append("breath must lead directly into payoff")
    return bad


def _validate_motion(plan: dict, expected_aspect: str) -> list[str]:
    bad, motion = [], plan.get("motion_assets") or {}
    if motion.get("aspect") != expected_aspect:
        bad.append("motion asset aspect mismatch")
    cues = motion.get("cues") or []
    if sum(cue.get("role") == "transition" for cue in cues) > 2:
        bad.append("too many motion transitions")
    if sum(cue.get("role") == "overlay" for cue in cues) > 2:
        bad.append("too many motion overlays")
    if any(not cue.get("asset_id") or not cue.get("path") for cue in cues):
        bad.append("motion cue missing asset reference")
    return bad


def _validate_template_system(plan: dict, expected_aspect: str) -> list[str]:
    bad, templates = [], plan.get("template_system") or {}
    if templates.get("style") not in EDITORIAL_STYLES:
        bad.append("unknown editorial template style")
    if templates.get("aspect") != expected_aspect:
        bad.append("editorial template aspect mismatch")
    if not templates.get("roles"):
        bad.append("missing editorial template roles")
    program = templates.get("program") or {}
    if templates.get("compiler") != "hao-template-compiler-v2":
        bad.append("missing component template compiler")
    program_format = "shorts" if plan.get("format") == "short" else "longform"
    if not program.get("plans") or program.get("format") != program_format:
        bad.append("missing or mismatched template program")
    if len(program.get("signatures") or []) != len(set(program.get("signatures") or [])):
        bad.append("template program repeats a fatigued signature")
    if any((row.get("render_adapter") or {}).get("full_screen_card")
           for row in program.get("plans") or []):
        bad.append("generic full-screen template scene is forbidden")
    return bad


def _validate_aesthetic_system(plan: dict) -> list[str]:
    bad, system = [], plan.get("aesthetic_system") or {}
    if system.get("standard_id") != "public-aesthetic-standard":
        bad.append("missing creator aesthetic standard")
    if not system.get("primary_family") or not system.get("allowed_templates"):
        bad.append("incomplete aesthetic style route")
    style = (plan.get("template_system") or {}).get("style")
    if style not in (system.get("allowed_templates") or []):
        bad.append("template style is outside aesthetic domain route")
    if not (system.get("format_rule") or {}).get("rule"):
        bad.append("missing format-specific aesthetic rule")
    required = {"mrbeast_information_energy", "yingshi_hurricane_cinematic_craft"}
    if set(system.get("formal_benchmarks") or []) != required:
        bad.append("both MrBeast and 影視颶風 benchmarks are required")
    if not system.get("parity_claim_policy"):
        bad.append("missing effect parity claim policy")
    craft = plan.get("mediastorm_craft") or {}
    if craft.get("system") != "hao-mediastorm-craft-v1":
        bad.append("missing evidence-gated 影視颶風 craft planner")
    transitions = (craft.get("editing") or {}).get("transitions") or []
    if any(row.get("status") == "READY" and row.get("missing") for row in transitions):
        bad.append("影視颶風 transition claims READY without evidence")
    if any(row.get("selected") != "clean_cut" for row in transitions):
        bad.append("visual planning cannot approve expressive transitions before shot-pair evidence")
    compiled = plan.get("design_system_v6") or {}
    if compiled.get("compiler") != "public-design-system-v6":
        bad.append("missing v6 design DNA compiler")
    source = compiled.get("source") or {}
    partition = source.get("learning_partition") or {}
    if not source.get("reference_count") or source.get("reference_count") != sum(partition.values()):
        bad.append("v6 design DNA source count must match its public learning partition")
    if (compiled.get("route") or {}).get("primary_family") != system.get("primary_family"):
        bad.append("v6 design route disagrees with aesthetic system")
    information = plan.get("high_information_system") or {}
    if information.get("system") != "hao-high-information-editing-v1":
        bad.append("missing evidence-gated high-information editing system")
    if information.get("selected"):
        bad.append("visual director cannot preselect effects before evidence exists")
    system_3d = plan.get("three_d_system") or {}
    if system_3d.get("system") != "hao-3d-system-v1":
        bad.append("missing 3D capability route")
    if system_3d.get("status") == "READY" and system_3d.get("missing"):
        bad.append("3D route claims READY with missing prerequisites")
    if not system_3d.get("truth_boundary"):
        bad.append("3D route missing truth boundary")
    return bad


def _validate_budget_reference(data: dict | None, *, expected: str,
                               path_error: str, budget_error: str) -> list[str]:
    if not data:
        return []
    bad = []
    if data.get("packet", data.get("plan")) != expected:
        bad.append(path_error)
    if int(data.get("estimated_tokens", 10**9)) > int(data.get("max_tokens", 0)):
        bad.append(budget_error)
    return bad


def validate_visual_plan(plan: dict) -> list[str]:
    bad, duration = [], float(plan.get("duration", 0))
    if plan.get("domain", plan.get("genre")) not in PROFILES:
        bad.append("unknown domain")
    if plan.get("theme") not in THEMES:
        bad.append("unknown theme")
    shot_policy = plan.get("shot_selection") or {}
    if shot_policy.get("status") not in {"STYLE_CHOICE_REQUIRED", "AWAITING_SHOT_EVIDENCE"} or shot_policy.get("selected_shots"):
        bad.append("shot selection must remain an evidence-pending, non-applying draft")
    bad.extend(_validate_events(plan.get("events", []), duration))
    bad.extend(_validate_energy_curve(plan.get("energy_curve") or [], duration))
    if any(len(seq.get("shot_pattern") or []) < 3
           for seq in plan.get("sequence_plan") or []):
        bad.append("shot sequence has fewer than 3 functions")
    expected_aspect = "portrait" if plan.get("format") == "short" else "landscape"
    bad.extend(_validate_motion(plan, expected_aspect))
    bad.extend(_validate_template_system(plan, expected_aspect))
    bad.extend(_validate_aesthetic_system(plan))
    color = plan.get("color_system") or {}
    if not color.get("profile") or not color.get("one_look_only"):
        bad.append("missing single-look color system")
    if color.get("stage") != "source_before_graphics":
        bad.append("color grade must run before graphics")
    if float(color.get("base_strength", 1.0)) > float(color.get("max_strength", 0.0)):
        bad.append("color grade strength exceeds profile ceiling")
    trend = plan.get("trend_system") or {}
    if not trend.get("dominant_signal") or not trend.get("limit"):
        bad.append("missing restrained trend route")
    filters = plan.get("filter_system") or {}
    if filters.get("scope") != "all_formats_all_domains":
        bad.append("filter library must apply to every format and domain")
    if filters.get("grade") != color.get("profile"):
        bad.append("filter grade route must match the single-look color system")
    if filters.get("auto_selected"):
        bad.append("filter candidates cannot auto-select without shot evidence")
    bad.extend(validate_caption_system(plan.get("caption_system") or {}, duration))
    bad.extend(validate_shot_dynamics_system(plan.get("shot_dynamics_system") or {}, duration))
    runtime = plan.get("programmatic_runtime") or {}
    if runtime.get("schema") != "hao.motion-composition/v1":
        bad.append("missing canonical programmatic composition schema")
    if runtime.get("implementation") != "self_authored":
        bad.append("programmatic runtime must be self-authored")
    if runtime.get("scope") != "all_formats_all_domains":
        bad.append("programmatic runtime must apply to every format and domain")
    if runtime.get("third_party_video_frameworks") != "benchmark_only_not_runtime_dependencies":
        bad.append("third-party video frameworks may only be benchmarks")
    bad.extend(_validate_budget_reference(
        plan.get("context_budget"), expected=PACKET_NAME,
        path_error="context packet must use stable current path",
        budget_error="context packet exceeds token budget",
    ))
    bad.extend(_validate_budget_reference(
        plan.get("asset_intelligence"), expected=ASSET_PLAN_NAME,
        path_error="asset plan must use stable current path",
        budget_error="asset plan exceeds token budget",
    ))
    return bad
