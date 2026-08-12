# -*- coding: utf-8 -*-
"""Plan honest 2.5D/3D video enrichment and emit portable Blender jobs.

The planner distinguishes depth-stacked cards from true 3D and camera-solved
composites.  Missing meshes, calibration or tracking evidence never become a
fake "3D" claim; the route is downgraded explicitly.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROUTES = {
    "depth_cards": {
        "class": "2.5D", "requires": ["segmented_layers"],
        "use": "documents, screenshots, travel photos or evidence clusters",
        "fallback": "clean_2d_evidence",
    },
    "tracked_billboard": {
        "class": "2.5D", "requires": ["planar_track", "surface_reference"],
        "use": "labels or evidence attached to a flat real-world surface",
        "fallback": "tracked_2d_overlay",
    },
    "product_turntable": {
        "class": "true_3d", "requires": ["mesh", "material_refs", "light_reference"],
        "use": "battle tops, products, vehicles or branded objects with an owned mesh",
        "fallback": "verified_multiview_2d",
    },
    "camera_solved_composite": {
        "class": "true_3d_composite",
        "requires": ["camera_solve", "lens_data", "clean_plate", "shadow_plane", "light_reference"],
        "use": "CG object integrated into moving real footage",
        "fallback": "tracked_billboard",
    },
    "data_space": {
        "class": "true_3d", "requires": ["data_evidence", "scene_scale"],
        "use": "scale ladders, timelines, AI systems or spatial comparisons",
        "fallback": "depth_cards",
    },
    "extruded_type": {
        "class": "true_3d", "requires": ["licensed_font", "copy_approved"],
        "use": "selective hero word or number, never regular subtitles",
        "fallback": "premium_2d_type",
    },
}
FORMAT_SETTINGS = {
    "shorts": {"resolution": [1080, 1920], "safe_width": .84, "camera": "vertical_close"},
    "longform": {"resolution": [1920, 1080], "safe_width": .78, "camera": "landscape_context"},
}
MATERIALS = {
    "battle_top": {"roughness": .22, "metallic": .72, "sheen": "fast_narrow"},
    "vehicle": {"roughness": .18, "metallic": .62, "sheen": "long_body_panel"},
    "glass_ui": {"roughness": .08, "metallic": .05, "transmission": .82, "sheen": "spectral_edge"},
    "paper": {"roughness": .78, "metallic": 0.0, "sheen": "none"},
    "generic_product": {"roughness": .34, "metallic": .28, "sheen": "soft_diagonal"},
}


def plan_3d(route: str, *, format: str = "shorts", subject: str = "generic_product",
            available: list[str] | None = None, purpose: str = "explain") -> dict[str, Any]:
    if route not in ROUTES:
        raise ValueError("unknown 3D route %r" % route)
    format_key = "longform" if str(format).lower() in {"long", "longform", "youtube"} else "shorts"
    available_set = set(available or [])
    required = set(ROUTES[route]["requires"])
    missing = sorted(required - available_set)
    ready = not missing
    return {
        "schema_version": 1,
        "system": "hao-3d-system-v1",
        "requested_route": route,
        "capability_class": ROUTES[route]["class"],
        "status": "READY" if ready else "DOWNGRADED",
        "missing": missing,
        "effective_route": route if ready else ROUTES[route]["fallback"],
        "format": format_key,
        "frame": FORMAT_SETTINGS[format_key],
        "subject": subject,
        "purpose": purpose,
        "material_profile": MATERIALS.get(subject, MATERIALS["generic_product"]),
        "camera": {
            "movement": "one motivated move only",
            "parallax_required": ROUTES[route]["class"] != "2.5D",
            "solve_rule": "camera-solved routes require reprojection evidence and manual orientation review",
        },
        "lighting": {
            "key": "match real dominant direction or use neutral studio key",
            "rim": "selective separation only",
            "shadow": "shadow catcher required for real-footage composite",
        },
        "composite": {
            "source_grade_before_cg": True,
            "match_black_white_levels": True,
            "motion_blur_consistent": True,
            "occlusion_matte_required_when_crossing_subject": True,
        },
        "qa": [
            "silhouette readable at delivery size",
            "no object intersection or floating contact",
            "light direction and shadow softness match",
            "motion blur and depth of field match the plate",
            "all text remains inside format safe area",
            "Hao reviews start, peak and end frames",
        ],
        "truth_boundary": "2.5D is labelled 2.5D; true 3D and camera-solved composite are only claimed when prerequisites are present.",
    }


def validate_plan(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if plan.get("requested_route") not in ROUTES:
        errors.append("unknown requested route")
    if plan.get("status") == "READY" and plan.get("missing"):
        errors.append("READY plan cannot have missing prerequisites")
    if plan.get("requested_route") == "camera_solved_composite" and plan.get("status") == "READY":
        required = {"camera_solve", "lens_data", "clean_plate", "shadow_plane", "light_reference"}
        if not required.issubset(ROUTES["camera_solved_composite"]["requires"]):
            errors.append("camera composite contract drift")
    if not (plan.get("qa") and plan.get("truth_boundary")):
        errors.append("QA and truth boundary are required")
    return errors


def blender_job(plan: dict[str, Any], *, mesh_path: str = "", output: str = "render.png") -> dict[str, Any]:
    errors = validate_plan(plan)
    if errors:
        raise ValueError("invalid 3D plan: " + "; ".join(errors))
    if plan["status"] != "READY" or plan["requested_route"] not in {"product_turntable", "extruded_type"}:
        return {"status": "NOT_EMITTED", "reason": "route is downgraded or requires an interactive camera solve"}
    if plan["requested_route"] == "product_turntable" and not mesh_path:
        return {"status": "NOT_EMITTED", "reason": "mesh_path is required"}
    return {
        "status": "READY",
        "engine": "Blender",
        "scene": {
            "resolution": plan["frame"]["resolution"],
            "transparent": True,
            "subject": plan["subject"],
            "mesh_path": mesh_path or None,
            "material": plan["material_profile"],
            "camera_move": "turntable_22_5_degrees_or_single_dolly",
            "lights": ["large_area_key", "soft_fill", "selective_rim"],
            "output": output,
        },
        "handoff": "Generate a Blender scene from this manifest, render RGBA plus shadow pass, then composite through the normal colour and QA gates.",
    }


def self_test() -> None:
    missing = plan_3d("product_turntable", subject="battle_top", available=["material_refs"])
    assert missing["status"] == "DOWNGRADED" and "mesh" in missing["missing"]
    ready = plan_3d("product_turntable", format="longform", subject="battle_top",
                    available=["mesh", "material_refs", "light_reference"])
    assert ready["status"] == "READY" and ready["frame"]["resolution"] == [1920, 1080]
    assert not validate_plan(ready)
    assert blender_job(ready, mesh_path="subject.glb")["status"] == "READY"
    camera = plan_3d("camera_solved_composite", available=["camera_solve"])
    assert camera["status"] == "DOWNGRADED" and "shadow_plane" in camera["missing"]
    print("three_d_system self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan honest 2.5D/3D video enrichment")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest")
    plan = sub.add_parser("plan")
    plan.add_argument("route", choices=sorted(ROUTES))
    plan.add_argument("--format", default="shorts")
    plan.add_argument("--subject", default="generic_product")
    plan.add_argument("--available", nargs="*", default=[])
    plan.add_argument("--purpose", default="explain")
    plan.add_argument("--mesh-path", default="")
    args = parser.parse_args(argv)
    if args.command == "selftest":
        self_test()
        return 0
    result = plan_3d(args.route, format=args.format, subject=args.subject,
                     available=args.available, purpose=args.purpose)
    result["errors"] = validate_plan(result)
    result["blender_job"] = blender_job(result, mesh_path=args.mesh_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
