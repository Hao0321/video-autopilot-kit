"""Normalize public native-template instructions, without preparing or rendering.

This neutral module owns only a closed authoring vocabulary. Font availability,
physical layout, source evidence and complete artifact review remain downstream
obligations; a normalized direction is not a capability or quality receipt.
"""
from __future__ import annotations

import math
import re


NATIVE_REFERENCE_TEMPLATE_IDS = (
    "strike_reframe", "level_bridge", "comparison_pair", "context_stack",
    "evidence_takeover", "focus_wall", "brand_recap", "kinetic_network",
)
SUPPORTED_FORMATS = frozenset({
    "shorts", "reels", "vlog", "ai_short_drama", "longform", "podcast", "interview",
})
WHOLE_TEMPLATE_UNAVAILABLE_FORMATS = frozenset({"longform", "podcast", "interview"})
PALETTE_ROLES = frozenset({"surface", "text", "accent", "muted", "separator"})
TYPOGRAPHY_ROLES = frozenset({"headingFamily", "bodyFamily"})


def _closed_object(value, keys, label):
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(label + " requires exactly its declared fields")
    return value


def _relative_luminance(rgb):
    linear = []
    for offset in (1, 3, 5):
        channel = int(rgb[offset:offset + 2], 16) / 255
        linear.append(channel / 12.92 if channel <= 0.04045
                      else ((channel + 0.055) / 1.055) ** 2.4)
    return sum(channel * weight for channel, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def _contrast_ratio(first, second):
    values = sorted((_relative_luminance(first), _relative_luminance(second)))
    return (values[1] + 0.05) / (values[0] + 0.05)


def normalize_native_graphic_direction(raw, *, format="shorts"):
    """Return an owned, exact native authoring projection or reject the input."""
    if not isinstance(format, str) or format not in SUPPORTED_FORMATS:
        raise ValueError("native graphic direction requires a supported format")
    if format in WHOLE_TEMPLATE_UNAVAILABLE_FORMATS:
        raise ValueError("whole-board native template direction is unavailable for continuous longform UI and narration")
    direction = _closed_object(raw, {"templateId", "graphicCadence", "style"}, "native graphic direction")
    template = direction["templateId"]
    cadence = direction["graphicCadence"]
    if not isinstance(template, str) or template not in NATIVE_REFERENCE_TEMPLATE_IDS:
        raise ValueError("unknown native reference template")
    # Cadence timings live in Editkin's editkin.graphic-cadence/v1 profile; this
    # helper only admits the closed vocabulary ("kinetic" is the authoring default).
    if not isinstance(cadence, str) or cadence not in {"legacy", "brisk", "kinetic"}:
        raise ValueError("unknown native graphic cadence")

    style = direction["style"]
    if (not isinstance(style, dict) or not {"palette", "typography"} <= set(style)
            or not set(style) <= {"palette", "typography", "animationSpeed"}):
        raise ValueError("native style requires complete palette and typography with optional animationSpeed")
    palette = _closed_object(style["palette"], PALETTE_ROLES, "native palette")
    if any(not isinstance(color, str) or re.fullmatch(r"#[0-9a-fA-F]{6}", color) is None
           for color in palette.values()):
        raise ValueError("native palette colors must be six-digit RGB text")
    typography = _closed_object(style["typography"], TYPOGRAPHY_ROLES, "native typography")
    if any(not isinstance(family, str) or not family.strip() or len(family.strip()) > 80
           for family in typography.values()):
        raise ValueError("native font families must be bounded nonempty text; actual font bytes remain required")
    speed = style.get("animationSpeed", 1)
    # Test the numeric type before comparisons; booleans are not authoring rates.
    if type(speed) not in (int, float) or not 0.5 <= speed <= 2 or not math.isfinite(speed):
        raise ValueError("native animationSpeed must be a finite non-boolean number from .5 to 2")
    if (_contrast_ratio(palette["surface"], palette["text"]) < 4.5
            or _contrast_ratio(palette["surface"], palette["muted"]) < 3):
        raise ValueError("native palette needs text contrast >=4.5 and muted contrast >=3 against surface")

    return {
        "templateId": template,
        "graphicCadence": cadence,
        "style": {
            "palette": dict(palette),
            "typography": {role: family.strip() for role, family in typography.items()},
            "animationSpeed": speed,
        },
    }
