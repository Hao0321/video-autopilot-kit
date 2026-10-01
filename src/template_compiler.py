# -*- coding: utf-8 -*-
"""Reusable template-plan compiler (public distribution).

Compiles reusable components into small, fatigue-aware plans without retaining source-media paths.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import time
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from aesthetic_score import resolve_style_route
from design_system_v6 import compile_recipe


COMPILER_ID = "hao-template-compiler-v2"
SCHEMA_VERSION = 2
ROLE_ALIASES = {
    "hook": "first_frame", "thumbnail": "thumbnail", "chapter": "chapter",
    "quote": "proof", "stat": "proof", "proof": "proof",
    "compare": "comparison", "comparison": "comparison",
    "steps": "process", "process": "process", "lower_third": "lower_third",
    "end_card": "payoff", "payoff": "payoff", "background": "breath",
    "breath": "breath", "first_frame": "first_frame",
}
RENDER_ROLE = {
    "first_frame": "hook", "thumbnail": "thumbnail", "chapter": "chapter",
    "proof": "stat", "comparison": "compare", "process": "steps",
    "lower_third": "lower_third", "payoff": "hook", "breath": "background",
}
ROLE_COMPONENTS = {
    "first_frame": ("real_media", "promise_type", "subject_depth", "accent_mark"),
    "thumbnail": ("hero_subject", "claim_type", "tension_cue", "accent_mark"),
    "chapter": ("real_media", "chapter_index", "chapter_type", "progress_mark"),
    "proof": ("evidence_media", "metric_or_claim", "source_chip", "focus_mark"),
    "comparison": ("shared_baseline", "left_evidence", "right_evidence", "verdict_cue"),
    "process": ("context_media", "active_step", "focus_target", "progress_mark"),
    "lower_third": ("identity_or_location", "subject_clearance"),
    "payoff": ("hero_subject", "result_type", "clean_hold"),
    "breath": ("real_media", "clean_hold"),
}
LAYOUTS = {
    "first_frame": {
        "shorts": ("hero_center_type_top", "hero_full_bleed_type_band", "detail_first_stack"),
        "longform": ("hero_right_type_left", "evidence_full_bleed_corner_type", "hero_center_low_type"),
    },
    "thumbnail": {
        "shorts": ("hero_center_claim_top", "versus_split_vertical"),
        "longform": ("hero_right_claim_left", "versus_split_horizontal", "scale_comparison"),
    },
    "chapter": {
        "shorts": ("footage_overlay_index", "detail_hold_type_rail"),
        "longform": ("footage_overlay_index", "wide_context_type_rail", "chapter_bridge_split"),
    },
    "proof": {
        "shorts": ("evidence_full_bleed_callout", "metric_above_subject", "proof_zoom_window"),
        "longform": ("evidence_stage_metric", "proof_zoom_window", "source_sidecar"),
    },
    "comparison": {
        "shorts": ("stacked_shared_scale", "versus_split_vertical"),
        "longform": ("split_shared_scale", "versus_split_horizontal", "foreground_background_scale"),
    },
    "process": {
        "shorts": ("active_step_focus", "screen_window_step_rail"),
        "longform": ("screen_window_step_rail", "active_step_focus", "context_detail_progress"),
    },
    "lower_third": {
        "shorts": ("compact_subject_side", "location_pin_safe"),
        "longform": ("compact_subject_side", "identity_rail_safe"),
    },
    "payoff": {
        "shorts": ("hero_clean_result", "result_full_bleed_hold"),
        "longform": ("hero_clean_result", "wide_result_hold", "result_then_reaction"),
    },
    "breath": {
        "shorts": ("clean_detail_hold",), "longform": ("clean_wide_hold", "clean_detail_hold"),
    },
}
FORMAT_CONTRACTS = {
    "shorts": {
        "aspect": "9:16", "safe_area": {"x": .075, "top": .10, "bottom": .18},
        "max_components": 5, "type_lines": [1, 3], "hold_sec": [.35, 1.4],
    },
    "longform": {
        "aspect": "16:9", "safe_area": {"x": .055, "top": .07, "bottom": .10},
        "max_components": 6, "type_lines": [1, 2], "hold_sec": [.55, 2.4],
    },
}
STYLE_MOTIFS = {
    "cobalt_poetry": ("editorial_rule", "microtype"),
    "shape_play": ("organic_shape", "hand_line"),
    "lime_aura": ("soft_bloom", "grain"),
    "night_signal": ("selective_neon", "scan_grain"),
    "electric_lab": ("signal_line", "technical_mark"),
    "travel_journal": ("route_mark", "paper_edge"),
    "food_pop": ("appetite_colour", "studio_shadow"),
    "food_editorial": ("vertical_type", "paper_rule"),
    "food_steam": ("warm_bloom", "steam_depth"),
    "food_heritage": ("heritage_rule", "ink_accent"),
    "matcha_fresh": ("soft_shape", "cream_contrast"),
    "brush_rush": ("brush_scale", "stamp_accent"),
    "festival_block": ("ticket_block", "diagonal_energy"),
    "cyan_lab": ("selection_mark", "clean_ui_plane"),
    "holo_future": ("spectral_light", "glass_depth"),
    "morph_prism": ("spectral_form", "clean_stage"),
}
MOTION_BY_ROLE = {
    "first_frame": "subject_then_type_reveal", "thumbnail": "still_only",
    "chapter": "index_wipe_on_cut", "proof": "track_or_focus_then_hold",
    "comparison": "shared_baseline_then_contrast", "process": "one_step_then_focus",
    "lower_third": "short_slide_then_lock", "payoff": "clean_reveal_then_long_hold",
    "breath": "no_graphic_entry",
}


def _format_key(value: str) -> str:
    key = str(value or "shorts").lower()
    if key in {"short", "shorts", "reel", "reels", "portrait", "9:16"}:
        return "shorts"
    if key in {"long", "longform", "youtube", "landscape", "16:9"}:
        return "longform"
    raise ValueError("unknown format %r" % value)


def _role_key(value: str) -> str:
    key = ROLE_ALIASES.get(str(value or "proof").lower())
    if not key:
        raise ValueError("unknown template role %r" % value)
    return key


def _copy_shape(text: str) -> dict[str, int]:
    value = str(text or "")
    return {
        "length": min(80, len(value)),
        "cjk": len(re.findall(r"[\u3400-\u9fff]", value)),
        "latin": len(re.findall(r"[A-Za-z]", value)),
        "digits": len(re.findall(r"\d", value)),
    }


def _digest(value: Any, length: int = 12) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:length]


def _choose(candidates: Iterable[str], seed: Any, recent: Iterable[str] = ()) -> str:
    rows = tuple(dict.fromkeys(candidates))
    if not rows:
        raise ValueError("candidate set must not be empty")
    recent_counts = Counter(str(value) for value in recent)
    minimum = min(recent_counts.get(value, 0) for value in rows)
    fresh = [value for value in rows if recent_counts.get(value, 0) == minimum]
    return fresh[int(_digest(seed, 8), 16) % len(fresh)]


def _style_candidates(route: dict[str, Any]) -> tuple[str, ...]:
    values = tuple(route.get("allowed_templates") or ())
    return values or (str(route.get("primary_template") or "shape_play"),)


class PlanCache:
    """Content-safe structural cache; literal copy and media never enter it."""

    def __init__(self, directory: str | Path | None = None):
        self.directory = Path(directory).expanduser().resolve() if directory else None

    def _path(self, key: str) -> Path | None:
        return self.directory / (key + ".json") if self.directory else None

    def get(self, key: str) -> dict[str, Any] | None:
        path = self._path(key)
        if not path or not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return value if value.get("compiler") == COMPILER_ID else None

    def put(self, key: str, value: dict[str, Any]) -> None:
        path = self._path(key)
        if not path:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)


def compile_template_plan(domain: str, format: str, role: str, *,
                          title: str = "", energy: float = .65,
                          subject: str = "real_footage", seed: Any = 0,
                          style_hint: str | None = None,
                          recent_signatures: Iterable[str] = (),
                          recent_styles: Iterable[str] = (),
                          recent_layouts: Iterable[str] = (),
                          cache_dir: str | Path | None = None) -> dict[str, Any]:
    fmt, semantic_role = _format_key(format), _role_key(role)
    route = resolve_style_route(domain, fmt)
    candidates = _style_candidates(route)
    if style_hint:
        if style_hint not in candidates:
            raise ValueError("style hint is outside the domain route: " + style_hint)
        style = style_hint
    else:
        style = _choose(candidates, (domain, fmt, semantic_role, seed), recent_styles)
    layout = _choose(LAYOUTS[semantic_role][fmt], (style, semantic_role, seed), recent_layouts)
    signature = "%s:%s:%s:%s" % (style, fmt, semantic_role, layout)
    if signature in set(recent_signatures):
        layout = _choose(LAYOUTS[semantic_role][fmt], (style, semantic_role, seed, "rotate"),
                         [item.rsplit(":", 1)[-1] for item in recent_signatures])
        signature = "%s:%s:%s:%s" % (style, fmt, semantic_role, layout)
    if signature in set(recent_signatures) and not style_hint:
        used_styles = [str(item).split(":", 1)[0] for item in recent_signatures]
        style = _choose(candidates, (domain, fmt, semantic_role, seed, "style-rotate"), used_styles)
        signature = "%s:%s:%s:%s" % (style, fmt, semantic_role, layout)
    structural_input = {
        "compiler": COMPILER_ID, "schema": SCHEMA_VERSION, "domain": route["domain"],
        "format": fmt, "role": semantic_role, "style": style, "layout": layout,
        "copy_shape": _copy_shape(title), "energy_band": round(max(0, min(1, energy)) * 4) / 4,
        "subject_kind": re.sub(r"[^a-z0-9_-]+", "_", subject.lower())[:32],
    }
    cache_key = _digest(structural_input, 24)
    cache = PlanCache(cache_dir)
    cached = cache.get(cache_key)
    if cached:
        result = deepcopy(cached)
        result["cache"] = {"hit": True, "key": cache_key, "content_safe": True}
        return result
    recipe = compile_recipe(route["domain"], fmt, semantic_role, energy=energy, subject=subject)
    components = list(ROLE_COMPONENTS[semantic_role])
    background_mode = "real_media" if semantic_role not in {"thumbnail"} else "hero_subject"
    plan = {
        "schema_version": SCHEMA_VERSION, "compiler": COMPILER_ID,
        "route": {"domain": route["domain"], "format": fmt, "role": semantic_role,
                  "style": style, "layout": layout},
        "signature": signature,
        "render_adapter": {"legacy_role": RENDER_ROLE[semantic_role],
                           "mode": "overlay_or_composite", "full_screen_card": False},
        "components": components,
        "component_motifs": list(STYLE_MOTIFS.get(style, ("accent_rule",))),
        "background": {"mode": background_mode, "generated_fill_allowed": False,
                       "grid_usage": "texture_only_never_default_opener"},
        "copy_slots": {"title": structural_input["copy_shape"], "literal_copy_cached": False},
        "format_contract": FORMAT_CONTRACTS[fmt],
        "motion": {"preset": MOTION_BY_ROLE[semantic_role], "reason_required": True,
                   "generic_fullscreen_transition": False, "clean_hold_after_impact": True},
        "design_recipe": recipe,
        "guardrails": [
            "real footage or evidence remains dominant",
            "never expose HOOK, LOWER THIRD, SHAPE / PLAY or other template role labels",
            "do not insert a full-screen template between usable shots",
            "reflow for the target aspect; never center-crop another format",
            "a template is a composition plan, not a mandatory scene",
        ],
    }
    compact = "tpl2 %s/%s/%s style=%s layout=%s parts=%s motion=%s" % (
        fmt, semantic_role, route["domain"], style, layout, "+".join(components),
        MOTION_BY_ROLE[semantic_role],
    )
    plan["compact_instruction"] = compact
    plan["efficiency"] = {
        "structural_cache_key": cache_key, "prompt_chars": len(compact),
        "literal_copy_in_prompt": False, "media_paths_in_plan": False,
        "single_component_registry": True,
    }
    plan["cache"] = {"hit": False, "key": cache_key, "content_safe": True}
    quality = score_template_plan(plan, recent_signatures)
    plan["quality"] = quality
    if quality["status"] != "GREEN":
        raise ValueError("template plan blocked: " + "; ".join(quality["errors"]))
    stored = deepcopy(plan)
    stored.pop("cache", None)
    cache.put(cache_key, stored)
    return plan


def compile_template_program(domain: str, format: str, roles: Iterable[str], *,
                             title: str = "", energy: float = .65,
                             subject: str = "real_footage", seed: Any = 0,
                             style_hint: str | None = None,
                             recent_signatures: Iterable[str] = (),
                             cache_dir: str | Path | None = None) -> dict[str, Any]:
    normalized = list(dict.fromkeys(["first_frame", *(_role_key(role) for role in roles), "payoff"]))
    fmt = _format_key(format)
    route = resolve_style_route(domain, fmt)
    candidates = _style_candidates(route)
    if style_hint:
        if style_hint not in candidates:
            raise ValueError("program style hint is outside the domain route: " + style_hint)
        program_style = style_hint
    elif recent_signatures:
        program_style = _choose(
            candidates, (domain, fmt, seed, "program-style"),
            [str(value).split(":", 1)[0] for value in recent_signatures],
        )
    else:
        program_style = str(route.get("primary_template") or candidates[0])
    recent = list(recent_signatures)
    plans = []
    styles: list[str] = []
    layouts: list[str] = []
    for index, role in enumerate(normalized):
        plan = compile_template_plan(
            domain, format, role, title=title, energy=energy, subject=subject,
            seed=(seed, index), style_hint=program_style, recent_signatures=recent,
            recent_styles=styles[-2:], recent_layouts=layouts[-3:], cache_dir=cache_dir,
        )
        plans.append(plan)
        recent.append(plan["signature"])
        styles.append(plan["route"]["style"])
        layouts.append(plan["route"]["layout"])
    compact = " | ".join(plan["compact_instruction"] for plan in plans)
    return {
        "schema_version": SCHEMA_VERSION, "compiler": COMPILER_ID,
        "domain": plans[0]["route"]["domain"], "format": plans[0]["route"]["format"],
        "program_style": program_style,
        "plans": plans, "signatures": [plan["signature"] for plan in plans],
        "compact_instruction": compact,
        "efficiency": {"plan_count": len(plans), "prompt_chars": len(compact),
                       "cache_hits": sum(bool(plan["cache"]["hit"]) for plan in plans)},
    }


def score_template_plan(plan: dict[str, Any], recent_signatures: Iterable[str] = ()) -> dict[str, Any]:
    errors: list[str] = []
    route = plan.get("route") or {}
    fmt, role = route.get("format"), route.get("role")
    components = plan.get("components") or []
    if plan.get("compiler") != COMPILER_ID:
        errors.append("unknown compiler")
    if fmt not in FORMAT_CONTRACTS or role not in ROLE_COMPONENTS:
        errors.append("invalid format or role")
    elif len(components) > FORMAT_CONTRACTS[fmt]["max_components"]:
        errors.append("component budget exceeded")
    if (plan.get("render_adapter") or {}).get("full_screen_card"):
        errors.append("generic full-screen template scene forbidden")
    if (plan.get("motion") or {}).get("generic_fullscreen_transition"):
        errors.append("generic full-screen transition forbidden")
    if (plan.get("background") or {}).get("grid_usage") != "texture_only_never_default_opener":
        errors.append("grid opener policy missing")
    if len(plan.get("compact_instruction") or "") > 420:
        errors.append("compact instruction exceeds token budget")
    raw = json.dumps(plan, ensure_ascii=False).lower()
    private_attachment_marker = "codex-remote-" + "attachments"
    drive_prefixes = tuple(
        f"{chr(code)}:{chr(92)}" for code in range(ord("a"), ord("z") + 1)
    )
    if any(token in raw for token in (private_attachment_marker, *drive_prefixes)):
        errors.append("private path leaked")
    if (plan.get("copy_slots") or {}).get("literal_copy_cached") is not False:
        errors.append("literal copy entered structural cache")
    if plan.get("signature") in set(recent_signatures):
        errors.append("template fatigue: signature repeated")
    return {"status": "GREEN" if not errors else "BLOCKED", "score": 100 if not errors else 0,
            "errors": errors}


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="template-compiler-") as folder:
        first = compile_template_plan("toy", "shorts", "hook", title="榮耀女武神 VS 黃金神杖",
                                      subject="battle_top", seed=7, cache_dir=folder)
        assert first["quality"]["status"] == "GREEN" and not first["cache"]["hit"]
        again = compile_template_plan("toy", "shorts", "hook", title="榮耀女武神 VS 黃金神杖",
                                      subject="battle_top", seed=7, cache_dir=folder)
        assert again["cache"]["hit"] and again["copy_slots"]["literal_copy_cached"] is False
        long = compile_template_plan("ai", "longform", "process", title="建立工作流程",
                                     subject="screen_evidence", seed=9)
        assert long["format_contract"]["aspect"] == "16:9"
        assert first["signature"] != long["signature"]
        rotated = compile_template_plan("toy", "shorts", "hook", title="對戰",
                                        subject="battle_top", seed=7,
                                        recent_signatures=[first["signature"]])
        assert rotated["signature"] != first["signature"]
        program = compile_template_program("travel", "shorts", ["hook", "chapter", "proof"],
                                           title="鶯歌一日遊", seed=11)
        assert len(program["plans"]) >= 4 and len(program["signatures"]) == len(set(program["signatures"]))
    print("template_compiler self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile reusable creator template components")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest")
    bench = sub.add_parser("benchmark")
    bench.add_argument("--runs", type=int, default=100)
    plan = sub.add_parser("plan")
    plan.add_argument("--domain", default="general")
    plan.add_argument("--format", default="shorts")
    plan.add_argument("--role", default="proof")
    plan.add_argument("--title", default="")
    args = parser.parse_args(argv)
    if args.command == "selftest":
        self_test()
        return 0
    if args.command == "benchmark":
        started = time.perf_counter()
        for index in range(max(1, args.runs)):
            compile_template_plan("ai", "longform", "process", title="AI 工作流程", seed=index)
        elapsed = (time.perf_counter() - started) * 1000
        print(json.dumps({"runs": args.runs, "total_ms": round(elapsed, 2),
                          "mean_ms": round(elapsed / max(1, args.runs), 3)}, indent=2))
        return 0
    result = compile_template_plan(args.domain, args.format, args.role, title=args.title)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
