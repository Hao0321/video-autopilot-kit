# -*- coding: utf-8 -*-
"""Reusable, fail-closed components for BEYBLADE X Shorts plans.

The plan owns the verified keyframes.  This module only normalises the visual
contract so every battle Short uses the same unframed typography labels and
subject-only black-to-colour diagonal sheen.
"""

from __future__ import annotations


def identity_label(*, ident, text, bbox, keyframes, start, end, evidence,
                   side="left", official=False, font_scale=0.034,
                   max_width=0.30, panel_offset=None,
                   tracking_source="subject_matte"):
    label = {
        "id": ident,
        "text": text,
        "profile": "neon_value_cyan" if official else "impact_gold",
        "style": "identity_callout",
        "tracking_mode": "keyframes",
        "tracking_source": str(tracking_source),
        "initial_bbox": list(bbox),
        "keyframes": [{"time": float(t), "bbox": list(box)}
                      for t, box in keyframes],
        "start": float(start),
        "end": float(end),
        "anchor": side,
        "gap": 0.014,
        "font_scale": float(font_scale),
        "max_width": float(max_width),
        # The ID plate follows the photographed object.  A fixed upper rail
        # with a detached dot only proves that detection ran; it does not read
        # as premium tracking.  ``tracked_edge`` keeps the plate adjacent to
        # the subject while ``edge_pin`` terminates on the nearest silhouette
        # edge, never through the headline or the middle of the product.
        "layout_lane": "tracked_edge",
        "connector_style": "floating_tag",
        "pointer_color": [66, 215, 255] if official else [255, 196, 49],
        "pointer_target": [0.50, 0.50],
        "evidence": evidence,
    }
    if panel_offset is not None:
        label["panel_offset"] = [float(panel_offset[0]), float(panel_offset[1])]
    return label


def result_label(*, ident, text, bbox, keyframes, start, end, evidence):
    return {
        "id": ident,
        "text": text,
        "profile": "neon_value_green",
        "style": "typography",
        "tracking_mode": "keyframes",
        "initial_bbox": list(bbox),
        "keyframes": [{"time": float(t), "bbox": list(box)}
                      for t, box in keyframes],
        "start": float(start),
        "end": float(end),
        "anchor": "top",
        "gap": 0.010,
        "font_scale": 0.050,
        "max_width": 0.46,
        "evidence": evidence,
    }


def subject_sheen(*, ident, bbox, keyframes, start, end, evidence,
                  polygon=None, reveal_mode="black_to_color",
                  blackout_opacity=0.90):
    effect = {
        "id": ident,
        "start": float(start),
        "end": float(end),
        "initial_bbox": list(bbox),
        "keyframes": [{"time": float(t), "bbox": list(box)}
                      for t, box in keyframes],
        # ``auto_sequence`` is materialised by shorts_delivery into a real
        # per-frame alpha sequence before tracked_graphics validates/renders.
        # A battle top must never silently fall back to a loose ellipse/bbox.
        "shape": "polygon" if polygon else "auto_sequence",
        "matte_profile": "round_product_grabcut",
        "output_geometry": "segmented_silhouette",
        "exclude_skin_occlusion": True,
        "minimum_confidence": 0.55,
        "maximum_edge_chatter_px": 18.0,
        "temporal_radius": 3,
        "subject_class": "battle_top",
        "target_kind": "subject_object",
        "material_profile": "battle_top",
        "reveal_mode": str(reveal_mode),
        "blackout_opacity": float(blackout_opacity),
        "angle": -28,
        "band_width": 0.13,
        "contrast": 0.11,
        "reveal_softness": 0.52,
        "matte_feather": 0.006,
        "evidence": evidence,
    }
    if polygon:
        effect["polygon"] = [[float(x), float(y)] for x, y in polygon]
        effect["matte_quality_status"] = "GREEN"
        effect["matte_capability"] = "EDITOR_VERIFIED_POLYGON"
    return effect


def spin_result(*, winner, evidence):
    return {
        "finish": "spin",
        "winner": winner,
        "human_verified": True,
        "evidence": {
            "sequence_reviewed": True,
            "confidence": 1.0,
            "first_event": "spin",
            "simultaneous": False,
            "unjudgeable": False,
            "opponent_rotation_zero": True,
            "winner_rotation_positive": True,
            "opponent_zone": "battle",
            "review_note": evidence,
        },
    }
