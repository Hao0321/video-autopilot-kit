# -*- coding: utf-8 -*-
"""Visual planning facade (public distribution).

Coordinates the public visual planning and delivery components.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import tempfile

from art_direction import THEMES
from asset_registry import PLAN_NAME as ASSET_PLAN_NAME, write_asset_plan
from context_router import PACKET_NAME, write_context_packet
from visual_plan_support import PROFILES

from visual_plan_composition import _caption_rows, infer_domain, _card_for, _format_kind, _make_energy_curve, _energy_at, _shot_target, _nearest_caption, _event_anchors, _visual_events, _sequence_plan, _assemble_visual_plan, plan_visual_rhythm


from visual_plan_validation import (
    _validate_events,
    _validate_energy_curve,
    _validate_motion,
    _validate_template_system,
    _validate_aesthetic_system,
    _validate_budget_reference,
    validate_visual_plan,
)


from visual_programmatic_delivery import (
    _write_programmatic_plan,
)


def write_visual_plan(path: str, **kwargs) -> dict:
    plan = plan_visual_rhythm(**kwargs)
    output_dir = os.path.dirname(os.path.abspath(path))
    os.makedirs(output_dir, exist_ok=True)
    if plan["format"] == "longform":
        from longform_maker.emphasis_overlays import build_emphasis_overlay_ass
        overlay_name = "current_emphasis_overlays.ass"
        build_emphasis_overlay_ass(
            plan["caption_system"].get("emphasis_overlays") or [],
            os.path.join(output_dir, overlay_name),
        )
        plan["caption_system"]["emphasis_overlay_ass"] = overlay_name
    context = write_context_packet(
        output_dir,
        mode="build",
        format="shorts" if plan["format"] == "short" else "longform",
        domain=plan["domain"],
        topic=kwargs.get("context_text", ""),
    )
    plan["context_budget"] = {
        "packet": PACKET_NAME,
        "estimated_tokens": context["budget"]["estimated_tokens"],
        "max_tokens": context["budget"]["max_tokens"],
        "cache_hit": context["runtime"]["cache_hit"],
    }
    asset_plan = write_asset_plan(
        output_dir,
        topic=kwargs.get("context_text", "") or plan["domain"],
        domain=plan["domain"],
        format="shorts" if plan["format"] == "short" else "longform",
        duration=plan["duration"],
        cues=kwargs.get("captions"),
        energy_curve=plan["energy_curve"],
    )
    selected_music = (asset_plan.get("music") or {}).get("selected") or {}
    plan["asset_intelligence"] = {
        "plan": ASSET_PLAN_NAME,
        "selected_bgm": selected_music.get("path"),
        "music_strategy": (asset_plan.get("music") or {}).get("strategy"),
        "cue_count": len(asset_plan.get("cues") or []),
        "registry_counts": asset_plan.get("registry_counts", {}),
        "estimated_tokens": asset_plan["token_budget"]["estimated_tokens"],
        "max_tokens": asset_plan["token_budget"]["max_tokens"],
        "cache_hit": asset_plan["runtime"]["cache_hit"],
    }
    _write_programmatic_plan(output_dir, plan)
    errors = validate_visual_plan(plan)
    if errors:
        raise AssertionError("visual plan invalid after context routing: " + "; ".join(errors))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    return plan


def _self_test() -> None:
    from visual_director_commands import _self_test as implementation
    return implementation(globals())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=float, default=30.0)
    ap.add_argument("--genre", default="ai")
    ap.add_argument("--format", default="auto")
    ap.add_argument("--shot-style", default="auto")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    _self_test()
    plan = plan_visual_rhythm(args.duration, genre=args.genre, format=args.format, seed="cli", shot_style=args.shot_style)
    if args.out:
        write_visual_plan(args.out, duration=args.duration, genre=args.genre,
                          format=args.format, seed="cli", shot_style=args.shot_style)
        print("visual plan ->", args.out)
    else:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
