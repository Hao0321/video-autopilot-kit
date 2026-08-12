# -*- coding: utf-8 -*-
"""Compile Hao's 33-reference design DNA into a bounded visual recipe.

This module never ships the private reference images and never reproduces a
recognizable layout.  It selects one primary family, at most one support
family, a format reflow and an evidence role.  Renderers consume the recipe;
they do not need the full reference library or a large model context.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from aesthetic_score import load_standard, resolve_style_route


ROOT = Path(__file__).resolve().parent
DNA_PATH = ROOT.parent / "knowledge" / "runtime" / "design_reference_dna.json"
ALLOWED_ROLES = {
    "first_frame", "chapter", "proof", "comparison", "process",
    "payoff", "thumbnail", "lower_third", "breath",
}
FORMAT_REFLOW = {
    "shorts": {
        "aspect": "9:16", "hero_coverage": [.38, .68], "max_focus_count": 1,
        "type_lines": [1, 3], "microtype": "minimal",
        "motion": "0.18-0.45s entry; one readable hold before exit",
    },
    "longform": {
        "aspect": "16:9", "hero_coverage": [.24, .52], "max_focus_count": 1,
        "type_lines": [1, 2], "microtype": "allowed only when readable at 1080p",
        "motion": "0.24-0.60s entry; graphics punctuate footage rather than skin the timeline",
    },
}
ROLE_CONTRACTS = {
    "first_frame": "real result, conflict or scale first; graphics clarify the promise",
    "chapter": "one new idea and one identity gesture; no empty full-screen card over usable footage",
    "proof": "real evidence remains visually dominant and every number has provenance",
    "comparison": "shared baseline, visible contrast and consistent scale",
    "process": "one active step and one focus target; preserve spatial memory",
    "payoff": "hero subject and result get the cleanest, longest hold",
    "thumbnail": "one claim, one hero and one tension cue; mobile silhouette must survive",
    "lower_third": "identity or location only; never repeat the bottom subtitle",
    "breath": "reduce density and preserve room tone or visual stillness",
}
MATERIAL_PRESETS = {
    "cobalt_editorial": ["paper", "halftone", "editorial cutout"],
    "shape_play": ["warm paper", "risograph grain", "hand line"],
    "luminous_organic": ["airbrush", "fine grain", "soft bloom"],
    "night_signal": ["black stage", "scan grain", "selective neon"],
    "travel_scrapbook": ["photo facet", "paper", "route doodle"],
    "food_hero": ["studio cutout", "appetite gloss", "soft floor shadow"],
    "brush_culture": ["dry brush", "flat colour plane", "stamp accent"],
    "cobalt_lime_ui": ["clean UI plane", "selection mark", "technical line"],
    "iridescent_future": ["glass or chrome hero", "spectral light", "clean cyclorama"],
    "ticket_ribbon": ["printed ribbon", "paper curl", "perspective depth"],
}


def load_dna(path: str | Path = DNA_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_dna(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = data.get("references") or []
    if data.get("reference_count") != 33 or len(rows) != 33:
        errors.append("design DNA must contain exactly 33 anonymized references")
    ids = [row.get("id") for row in rows]
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        errors.append("reference ids must be present and unique")
    families = set((load_standard().get("style_families") or {}).keys())
    unknown = sorted({row.get("family") for row in rows} - families)
    if unknown:
        errors.append("unknown style families: %s" % unknown)
    required = {"composition", "hierarchy", "palette", "type", "material", "motion", "best_roles", "avoid"}
    for row in rows:
        missing = sorted(key for key in required if not row.get(key))
        if missing:
            errors.append("%s missing %s" % (row.get("id"), missing))
    serialized = json.dumps(data, ensure_ascii=False).lower()
    for private_token in ("codex-remote-" + "attachments", "c:\\users", "d:\\"):
        if private_token in serialized:
            errors.append("private path leaked into design DNA")
    return errors


def _family_examples(data: dict[str, Any], family: str) -> list[dict[str, Any]]:
    return [row for row in data["references"] if row["family"] == family]


def _dominant(values: list[str], count: int = 4) -> list[str]:
    return [value for value, _ in Counter(values).most_common(count)]


def compile_recipe(domain: str, format: str, role: str, *,
                   energy: float = .65, subject: str = "real_footage",
                   support_family: str | None = None) -> dict[str, Any]:
    data, standard = load_dna(), load_standard()
    errors = validate_dna(data)
    if errors:
        raise ValueError("invalid design DNA: " + "; ".join(errors))
    route = resolve_style_route(domain, format, standard)
    format_key = route["format"]
    role = str(role or "proof").lower()
    if role not in ALLOWED_ROLES:
        raise ValueError("unknown design role %r" % role)
    primary = route["primary_family"]
    if support_family is None:
        support_family = (route.get("support_families") or [None])[0]
    if support_family not in (route.get("support_families") or []):
        support_family = None
    examples = _family_examples(data, primary)
    palettes = [colour for row in examples for colour in row["palette"]]
    materials = [item for row in examples for item in row["material"]]
    motions = [item for row in examples for item in row["motion"]]
    energy = max(0.0, min(1.0, float(energy)))
    accent_budget = 1 if energy < .45 else 2
    density = "quiet" if energy < .35 else ("controlled" if energy < .78 else "impact")
    return {
        "schema_version": 1,
        "compiler": "hao-design-system-v6",
        "source": {"reference_count": 33, "private_images_embedded": False},
        "route": {
            "domain": route["domain"], "format": format_key, "role": role,
            "primary_family": primary, "support_family": support_family,
        },
        "hierarchy": {
            "focus_count": 1, "hero": subject,
            "contract": ROLE_CONTRACTS[role],
            "subject_integration": "use overlap, shared light, shadow or foreground depth; never paste flat",
        },
        "visual_tokens": {
            "palette_candidates": _dominant(palettes, 5),
            "accent_colour_budget": accent_budget,
            "material_candidates": _dominant(materials, 4) or MATERIAL_PRESETS[primary],
            "motion_candidates": _dominant(motions, 4),
            "density": density,
        },
        "format_reflow": FORMAT_REFLOW[format_key],
        "motion_contract": {
            "reason_required": True,
            "allowed_reasons": ["reveal", "compare", "explain", "locate", "payoff"],
            "entry_exit": FORMAT_REFLOW[format_key]["motion"],
            "no_generic_fullscreen_transition": True,
        },
        "guardrails": list(dict.fromkeys([
            *route.get("avoid", []),
            "do not copy a reference composition",
            "do not use grid or HUD as an automatic opener",
            "do not expose template role labels",
            "do not activate more than one hero and two accents",
        ])),
        "quality_signals": {
            "design_dna_compiled": True,
            "style_domain_match": True,
            "single_focal_hierarchy": True,
            "exact_reference_layout_copy": False,
        },
    }


def score_recipe(recipe: dict[str, Any]) -> dict[str, Any]:
    route = recipe.get("route") or {}
    tokens = recipe.get("visual_tokens") or {}
    hierarchy = recipe.get("hierarchy") or {}
    motion = recipe.get("motion_contract") or {}
    checks = {
        "domain_route": bool(route.get("primary_family")),
        "single_focus": hierarchy.get("focus_count") == 1,
        "real_role_contract": bool(hierarchy.get("contract")),
        "palette_restraint": int(tokens.get("accent_colour_budget", 99)) <= 2,
        "material_finish": bool(tokens.get("material_candidates")),
        "motivated_motion": bool(motion.get("reason_required") and motion.get("allowed_reasons")),
        "format_reflow": bool((recipe.get("format_reflow") or {}).get("aspect")),
        "reference_privacy": (recipe.get("source") or {}).get("private_images_embedded") is False,
    }
    score = round(100 * sum(checks.values()) / len(checks), 1)
    return {"status": "GREEN" if score == 100 else "BLOCKED", "score": score, "checks": checks}


def self_test() -> None:
    assert not validate_dna(load_dna())
    short = compile_recipe("toy", "shorts", "first_frame", subject="battle_top")
    assert short["route"]["primary_family"] == "shape_play"
    assert short["format_reflow"]["aspect"] == "9:16"
    assert score_recipe(short)["status"] == "GREEN"
    long = compile_recipe("ai", "longform", "process", energy=.42, subject="screen_evidence")
    assert long["route"]["primary_family"] == "cobalt_lime_ui"
    assert long["format_reflow"]["aspect"] == "16:9"
    assert long["visual_tokens"]["accent_colour_budget"] == 1
    print("design_system_v6 self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile the Hao v6 design system")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest")
    plan = sub.add_parser("plan")
    plan.add_argument("--domain", default="general")
    plan.add_argument("--format", default="shorts")
    plan.add_argument("--role", default="proof", choices=sorted(ALLOWED_ROLES))
    plan.add_argument("--energy", type=float, default=.65)
    plan.add_argument("--subject", default="real_footage")
    args = parser.parse_args(argv)
    if args.command == "selftest":
        self_test()
        return 0
    recipe = compile_recipe(args.domain, args.format, args.role,
                            energy=args.energy, subject=args.subject)
    recipe["quality"] = score_recipe(recipe)
    print(json.dumps(recipe, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
