# -*- coding: utf-8 -*-
"""Redistributable design recipe compiler (public distribution).

Compiles an anonymized public seed catalog into bounded visual recipes for multiple formats.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
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
MINIMUM_PUBLIC_REFERENCE_COUNT = 1
ALLOWED_LEARNING_SCOPES = {"full_style", "layout_only", "art_direction"}
DEFAULT_LEARN_DIMENSIONS = {
    "composition", "hierarchy", "palette", "type", "material", "motion",
}
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
    "arcade_pop": ["sticker edge", "comic halftone", "flat colour burst"],
    "pixel_terminal": ["one-bit pixel", "bitmap window", "scan texture"],
    "japanese_lifestyle_calm": ["warm paper", "natural wood", "linen", "soft daylight"],
}
EXCLUSIVE_DISPLAY_FAMILIES = {"arcade_pop", "pixel_terminal", "iridescent_future"}
ROLE_LAYOUT_PREFERENCES = {
    "first_frame": ["centered", "diagonal", "corner_anchor", "image_bleed"],
    "chapter": ["enveloping", "curve", "centered", "image_colour_block"],
    "proof": ["nine_grid", "uniform_picture_size", "picture_center", "picture_split"],
    "comparison": ["picture_split", "picture_crossover", "multiple_image_misalignment", "nine_grid"],
    "process": ["segmentation", "diagonal", "curve", "nine_grid"],
    "payoff": ["centered", "image_bleed", "enveloping", "corner_anchor"],
    "thumbnail": ["centered", "diagonal", "corner_anchor", "image_bleed"],
    "lower_third": ["corner_anchor", "picture_split"],
    "breath": ["centered", "curve", "uniform_picture_size"],
}


def load_dna(path: str | Path = DNA_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_dna(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = data.get("references") or []
    if (data.get("reference_count") != len(rows) or
            len(rows) < MINIMUM_PUBLIC_REFERENCE_COUNT):
        errors.append("design DNA reference_count must match a non-empty public seed catalog")
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
        scope = row.get("learning_scope", "full_style")
        if scope not in ALLOWED_LEARNING_SCOPES:
            errors.append("%s has unknown learning_scope %r" % (row.get("id"), scope))
        dimensions = set(row.get("learn_dimensions") or DEFAULT_LEARN_DIMENSIONS)
        unknown_dimensions = sorted(dimensions - DEFAULT_LEARN_DIMENSIONS - {"image_placement", "type_placement"})
        if unknown_dimensions:
            errors.append("%s has unknown learn_dimensions %s" % (row.get("id"), unknown_dimensions))
        if scope == "layout_only" and dimensions & {"palette", "material", "motion"}:
            errors.append("%s layout-only reference leaks surface-style dimensions" % row.get("id"))
    serialized = json.dumps(data, ensure_ascii=False).lower()
    private_tokens = ("codex-remote-" + "attachments",) + tuple(
        f"{chr(code)}:{chr(92)}" for code in range(ord("a"), ord("z") + 1)
    )
    for private_token in private_tokens:
        if private_token in serialized:
            errors.append("private path leaked into design DNA")
    return errors


def _family_examples(data: dict[str, Any], family: str) -> list[dict[str, Any]]:
    return [row for row in data["references"] if row["family"] == family]


def _dominant(values: list[str], count: int = 4) -> list[str]:
    return [value for value, _ in Counter(values).most_common(count)]


def _learns(row: dict[str, Any], dimension: str) -> bool:
    return dimension in set(row.get("learn_dimensions") or DEFAULT_LEARN_DIMENSIONS)


def _dimension_candidates(rows: list[dict[str, Any]], dimension: str,
                          field: str, count: int, *, art_take: int = 1) -> list[str]:
    eligible = [row for row in rows if _learns(row, dimension)]
    art_rows = [row for row in eligible if row.get("learning_scope") == "art_direction"]

    def values(source: list[dict[str, Any]]) -> list[str]:
        output: list[str] = []
        for row in source:
            value = row[field]
            output.extend(value if isinstance(value, list) else [value])
        return output

    reserved = list(dict.fromkeys(values(art_rows)))[:art_take]
    ranked = _dominant(values(eligible), count)
    return list(dict.fromkeys([*reserved, *ranked]))[:count]


def _layout_primitives(data: dict[str, Any], role: str) -> list[str]:
    available = list(dict.fromkeys(
        primitive
        for row in data["references"]
        if row.get("learning_scope") == "layout_only"
        for primitive in row.get("layout_primitives", [])
    ))
    preferred = ROLE_LAYOUT_PREFERENCES[role]
    selected = [primitive for primitive in preferred if primitive in available]
    return selected[:4] or available[:4]


def _families_can_support(primary: str, support: str) -> bool:
    """Keep mutually complete high-energy display systems out of one frame."""
    return not (primary in EXCLUSIVE_DISPLAY_FAMILIES and
                support in EXCLUSIVE_DISPLAY_FAMILIES)


def _resolve_recipe_route(standard: dict[str, Any], domain: str, format: str,
                          role: str, support_family: str | None,
                          style_family: str | None) -> tuple[dict[str, Any], str, str, str, str | None]:
    route = resolve_style_route(domain, format, standard)
    format_key = route["format"]
    role = str(role or "proof").lower()
    if role not in ALLOWED_ROLES:
        raise ValueError("unknown design role %r" % role)
    allowed_families = [route["primary_family"], *(route.get("support_families") or [])]
    primary = str(style_family or route["primary_family"])
    if primary not in allowed_families:
        raise ValueError("style family %r is not approved for %s; choose from %s" %
                         (primary, route["domain"], allowed_families))
    if support_family is None:
        support_family = next((family for family in allowed_families
                               if family != primary and _families_can_support(primary, family)), None)
    if (support_family not in allowed_families or support_family == primary or
            not _families_can_support(primary, support_family)):
        support_family = None
    return route, format_key, role, primary, support_family


def _recipe_examples(data: dict[str, Any], primary: str) -> tuple[
        list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], Counter]:
    examples = _family_examples(data, primary)
    layout_examples = [row for row in data["references"]
                       if row.get("learning_scope") == "layout_only"]
    combined = list({row["id"]: row for row in [*examples, *layout_examples]}.values())
    composition = [row for row in combined if _learns(row, "composition")]
    hierarchy = [row for row in combined if _learns(row, "hierarchy")]
    partition = Counter(row.get("learning_scope", "full_style") for row in data["references"])
    return examples, composition, hierarchy, partition


def _compile_visual_tokens(examples: list[dict[str, Any]],
                           composition_examples: list[dict[str, Any]],
                           hierarchy_examples: list[dict[str, Any]],
                           primary: str, energy: float) -> dict[str, Any]:
    accent_budget = 1 if energy < .45 else 2
    density = "quiet" if energy < .35 else ("controlled" if energy < .78 else "impact")
    return {
        "palette_candidates": _dimension_candidates(examples, "palette", "palette", 5, art_take=2),
        "accent_colour_budget": accent_budget,
        "material_candidates": _dimension_candidates(examples, "material", "material", 4, art_take=2) or MATERIAL_PRESETS[primary],
        "motion_candidates": _dimension_candidates(examples, "motion", "motion", 4),
        "type_candidates": _dimension_candidates(examples, "type", "type", 3),
        "composition_candidates": _dimension_candidates(composition_examples, "composition", "composition", 3),
        "hierarchy_candidates": _dimension_candidates(hierarchy_examples, "hierarchy", "hierarchy", 3),
        "density": density,
    }


def _recipe_guardrails(route: dict[str, Any]) -> list[str]:
    return list(dict.fromkeys([
        *route.get("avoid", []),
        "do not copy a reference composition",
        "do not use grid or HUD as an automatic opener",
        "do not expose template role labels",
        "do not activate more than one hero and two accents",
        "do not mix arcade sticker, pixel terminal and iridescent chrome in one frame",
        "do not present retro windows, alerts or cursors as real product evidence",
        "do not use rainbow colour unless it belongs to one iridescent material hero",
        "do not copy a layout-board example literally or combine more than two composition primitives",
        "do not inherit grey placeholder colours from layout-only references",
        "iridescence belongs to one carrier only: object, hero type or geometric disc",
    ]))


def compile_recipe(domain: str, format: str, role: str, *,
                   energy: float = .65, subject: str = "real_footage",
                   support_family: str | None = None,
                   style_family: str | None = None) -> dict[str, Any]:
    data, standard = load_dna(), load_standard()
    errors = validate_dna(data)
    if errors:
        raise ValueError("invalid design DNA: " + "; ".join(errors))
    route, format_key, role, primary, support_family = _resolve_recipe_route(
        standard, domain, format, role, support_family, style_family
    )
    examples, composition_examples, hierarchy_examples, learning_partition = _recipe_examples(
        data, primary
    )
    energy = max(0.0, min(1.0, float(energy)))
    visual_tokens = _compile_visual_tokens(
        examples, composition_examples, hierarchy_examples, primary, energy
    )
    return {
        "schema_version": 1,
        "compiler": "public-design-system-v6",
        "source": {
            "reference_count": data["reference_count"],
            "private_images_embedded": False,
            "learning_partition": dict(sorted(learning_partition.items())),
        },
        "route": {
            "domain": route["domain"], "format": format_key, "role": role,
            "primary_family": primary, "support_family": support_family,
        },
        "hierarchy": {
            "focus_count": 1, "hero": subject,
            "contract": ROLE_CONTRACTS[role],
            "subject_integration": "use overlap, shared light, shadow or foreground depth; never paste flat",
        },
        "visual_tokens": visual_tokens,
        "typography_contract": {
            "type_voices": 2,
            "hero_type_is_structure": True,
            "utility_copy_is_secondary": True,
            "phone_legibility_required": True,
            "rule": "choose one display voice and one utility voice; never shrink the main idea into a small bottom caption",
        },
        "layout_contract": {
            "density_zones": "one impact cluster plus one quiet lane",
            "subject_type_interlock": "allow crop, overlap or behind/in-front layering only when the complete claim remains readable",
            "microtype": "finish and metadata only; never required to understand the frame",
            "primitive_candidates": _layout_primitives(data, role),
            "max_combined_primitives": 2,
            "planning_order": "choose one composition skeleton and image-placement rule before colour, material or motion",
            "scope_isolation": "layout-only references may influence position and hierarchy but never palette, material or motion",
        },
        "format_reflow": FORMAT_REFLOW[format_key],
        "motion_contract": {
            "reason_required": True,
            "allowed_reasons": ["reveal", "compare", "explain", "locate", "payoff"],
            "entry_exit": FORMAT_REFLOW[format_key]["motion"],
            "no_generic_fullscreen_transition": True,
        },
        "guardrails": _recipe_guardrails(route),
        "quality_signals": {
            "design_dna_compiled": True,
            "style_domain_match": True,
            "single_focal_hierarchy": True,
            "exact_reference_layout_copy": False,
            "layout_reference_surface_leak": False,
            "composition_skeleton_overload": False,
            "multiple_iridescent_carriers": False,
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
        "structural_typography": bool((recipe.get("typography_contract") or {}).get("hero_type_is_structure")),
        "density_control": bool((recipe.get("layout_contract") or {}).get("density_zones")),
        "layout_scope_isolation": bool((recipe.get("layout_contract") or {}).get("scope_isolation")),
        "reference_privacy": (recipe.get("source") or {}).get("private_images_embedded") is False,
    }
    score = round(100 * sum(checks.values()) / len(checks), 1)
    return {"status": "GREEN" if score == 100 else "BLOCKED", "score": score, "checks": checks}


def self_test() -> None:
    assert not validate_dna(load_dna())
    short = compile_recipe("toy", "shorts", "first_frame", subject="battle_top")
    assert short["route"]["primary_family"] == "arcade_pop"
    assert short["route"]["support_family"] not in EXCLUSIVE_DISPLAY_FAMILIES
    assert sum(short["source"]["learning_partition"].values()) == load_dna()["reference_count"]
    assert short["source"]["learning_partition"].get("layout_only", 0) >= 1
    assert "centered" in short["layout_contract"]["primitive_candidates"]
    assert short["format_reflow"]["aspect"] == "9:16"
    assert score_recipe(short)["status"] == "GREEN"
    calm = compile_recipe("travel", "longform", "chapter", subject="real_travel_footage")
    assert calm["route"]["primary_family"] == "travel_scrapbook"
    assert calm["visual_tokens"]["material_candidates"]
    long = compile_recipe("ai", "longform", "process", energy=.42, subject="screen_evidence")
    assert long["route"]["primary_family"] == "cobalt_lime_ui"
    assert long["format_reflow"]["aspect"] == "16:9"
    assert long["visual_tokens"]["accent_colour_budget"] == 1
    retro = compile_recipe("technology", "shorts", "chapter", subject="real_screen_evidence",
                           style_family="pixel_terminal")
    assert retro["route"]["primary_family"] == "pixel_terminal"
    assert retro["visual_tokens"]["type_candidates"]
    editorial = compile_recipe("design", "shorts", "comparison", subject="editorial_subject")
    assert "picture_split" in editorial["layout_contract"]["primitive_candidates"]
    assert "placeholder grey" not in editorial["visual_tokens"]["palette_candidates"]
    assert editorial["visual_tokens"]["palette_candidates"][0] == "ultramarine cobalt"
    holo = compile_recipe("fashion", "shorts", "first_frame", subject="hero_type")
    assert holo["visual_tokens"]["palette_candidates"][0] == "neutral silver grey"
    try:
        compile_recipe("food", "shorts", "first_frame", style_family="arcade_pop")
    except ValueError:
        pass
    else:
        raise AssertionError("arcade style must not leak into food")
    print("design_system_v6 self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile the public v6 design system")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest")
    plan = sub.add_parser("plan")
    plan.add_argument("--domain", default="general")
    plan.add_argument("--format", default="shorts")
    plan.add_argument("--role", default="proof", choices=sorted(ALLOWED_ROLES))
    plan.add_argument("--energy", type=float, default=.65)
    plan.add_argument("--subject", default="real_footage")
    plan.add_argument("--style-family", default="")
    args = parser.parse_args(argv)
    if args.command == "selftest":
        self_test()
        return 0
    recipe = compile_recipe(args.domain, args.format, args.role,
                            energy=args.energy, subject=args.subject,
                            style_family=args.style_family or None)
    recipe["quality"] = score_recipe(recipe)
    print(json.dumps(recipe, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
