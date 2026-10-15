"""Asset workshop plan; one implementation behind the compatibility facade."""
from __future__ import annotations

from mrbeast_source_map import asset_backlog as mrbeast_asset_backlog
from mrbeast_source_map import load_map as load_mrbeast_source_map
from mrbeast_source_map import validate_map as validate_mrbeast_source_map


NONREAL_EDITORIAL_DOMAINS = {"travel", "food", "cafe"}

def default_plan() -> dict:
    """Return the durable expansion backlog, not a one-off prompt list."""
    source_map = load_mrbeast_source_map()
    source_map_errors = validate_mrbeast_source_map(source_map)
    if source_map_errors:
        raise ValueError("invalid MrBeast source map: " + "; ".join(source_map_errors))
    return {
        "schema_version": 2,
        "strategy": "Real footage first. Build editable rigs, materials, emitters and source scenes; prototype one motion test, obtain Hao approval, then scale only the approved family.",
        "benchmark_translation": {
            "high_information_editing": ["event-readable silhouette", "tracked value/state overlays", "reveal/payoff objects"],
            "cinematic_craft": ["material realism", "subject-masked light", "sound-design-ready event cues", "controlled contrast"],
            "originality_boundary": "Functional principles only; no creator logos, fonts, layouts, characters or protected assets.",
        },
        "mrbeast_source_map": {
            "version": source_map.get("version"),
            "effect_count": len(source_map.get("effects", [])),
            "production_jobs": mrbeast_asset_backlog(source_map),
            "rule": "Tracking, roto, camera solve, lighting, copy, timing and grade stay per-shot; no fixed PNG may pretend to be a finished effect.",
        },
        "batches": [
            {"id": "photoreal-production-assets-v1", "role": "photoreal_cutout", "count": 0,
             "domains": ["ai", "toy", "product", "business", "travel", "food"],
             "status": "rejected_iconlike_output_do_not_reingest"},
            {"id": "photoreal-product-3d-v1", "role": "prerendered_3d", "count": 8,
             "domains": ["toy", "product", "automotive"], "status": "taste_board_required"},
            {"id": "japanese-lifestyle-components-v1", "role": "japanese_lifestyle_illustration", "count": 0,
             "domains": ["travel", "food", "cafe"], "status": "rejected_iconlike_output_do_not_reingest"},
            {"id": "keyed-vfx-derivatives-v1", "role": "vfx_overlay", "count": 0,
             "domains": ["general"], "status": "derive_from_approved_black_or_white_plate"},
        ],
        "gates": {
            "alpha_required_for_atoms": True,
            "minimum_coverage_ratio": 0.05,
            "maximum_coverage_ratio": 0.92,
            "exact_duplicate_blocked": True,
            "human_visual_review_required": True,
            "selection_requires_approval": True,
            "asset_fatigue_tracked": True,
            "taste_board_approval_before_bulk_generation": True,
            "motion_test_approval_before_bulk_generation": True,
            "source_rig_required_for_type_hud_tracking_and_3d": True,
            "fixed_raster_text_does_not_count_as_a_rig": True,
            "tracking_roto_camera_solve_are_never_counted_as_assets": True,
            "nonreal_editorial_domains": sorted(NONREAL_EDITORIAL_DOMAINS),
            "icons_are_ui_annotations_not_narrative_assets": True,
            "icon_style": "single-color flat minimal silhouette",
        },
    }
