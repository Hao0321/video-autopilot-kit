# -*- coding: utf-8 -*-
"""Presentation primitives for tracked graphics.

This module owns how verified tracking state is drawn: editable plates,
connectors, arrows, subject locks and subject-matte sheens.  It deliberately
does not own trackers, video I/O, validation or CLI behavior.  Callers supply
the verified bbox resolver used by subject effects so this layer cannot invent
tracking evidence.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Callable, Protocol

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from tracked_typography import (
    TEXT_PROFILES,
    animate_identity_plate,
    animate_text_plate,
    font as _font,
    render_text_plate,
)


SHEEN_MATERIALS = {
    "battle_top": {
        "opacity": .62, "band_width": .13, "glow": .018,
        "secondary": .24, "core": .78, "contrast": .11,
    },
    "vehicle_paint": {
        "opacity": .76, "band_width": .09, "glow": .016,
        "secondary": .22, "core": .90, "contrast": .18,
    },
    "glass": {
        "opacity": .68, "band_width": .075, "glow": .030,
        "secondary": .46, "core": .92, "contrast": .08,
    },
    "plastic_product": {
        "opacity": .74, "band_width": .13, "glow": .021,
        "secondary": .25, "core": .91, "contrast": .17,
    },
    "generic_product": {
        "opacity": .72, "band_width": .125, "glow": .020,
        "secondary": .22, "core": .90, "contrast": .16,
    },
}


class TrackPresentationState(Protocol):
    """Read-only state needed to present one tracked label."""

    config: dict[str, Any]
    frame_width: int
    frame_height: int
    smooth_box: tuple[float, float, float, float] | None
    base_plate: Image.Image | None


def _identity_callout_position(*, subject: tuple[float, float, float, float],
                               plate_size: tuple[int, int], preferred: str,
                               gap: int, margin: int,
                               frame_size: tuple[int, int]) -> tuple[int, int, str]:
    """Place an identity label adjacent to, never across, its subject."""
    x, y, w, h = subject
    plate_w, plate_h = plate_size
    frame_w, frame_h = frame_size
    candidates = {
        "left": (x - plate_w - gap, y + h * .5 - plate_h * .5),
        "right": (x + w + gap, y + h * .5 - plate_h * .5),
        "top": (x + w * .5 - plate_w * .5, y - plate_h - gap),
        "bottom": (x + w * .5 - plate_w * .5, y + h + gap),
    }
    opposite = {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}
    order = [preferred, opposite.get(preferred, "right"), "top", "bottom", "left", "right"]
    seen: set[str] = set()
    for side in order:
        if side in seen or side not in candidates:
            continue
        seen.add(side)
        px, py = candidates[side]
        if (px >= margin and py >= margin and
                px + plate_w <= frame_w - margin and py + plate_h <= frame_h - margin):
            return round(px), round(py), side
    clearance = {
        "left": x - margin,
        "right": frame_w - margin - (x + w),
        "top": y - margin,
        "bottom": frame_h - margin - (y + h),
    }
    side = max(clearance, key=clearance.get)
    px, py = candidates[side]
    px = min(max(margin, round(px)), frame_w - plate_w - margin)
    py = min(max(margin, round(py)), frame_h - plate_h - margin)
    return px, py, side


def _telemetry_plate(text: str, frame_height: int, max_width: int) -> Image.Image:
    """Render an editable cinematic telemetry plate, not a flat sticker."""
    font_px = max(38, round(frame_height * .064))
    value = render_text_plate(text, "price_white", font_px, max_width=round(max_width * .72))
    width = min(max_width, max(value.width + round(frame_height * .085), round(frame_height * .24)))
    height = max(value.height + round(frame_height * .040), round(frame_height * .105))
    pad = max(4, round(frame_height * .007))
    radius = max(12, round(height * .15))
    plate = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    chroma = Image.new("RGBA", plate.size, (0, 0, 0, 0))
    chroma_draw = ImageDraw.Draw(chroma, "RGBA")
    chroma_draw.rounded_rectangle(
        (pad - 3, pad + 2, width - pad - 3, height - pad + 2),
        radius=radius, outline=(255, 53, 96, 115), width=max(2, pad // 2),
    )
    chroma_draw.rounded_rectangle(
        (pad + 3, pad - 2, width - pad + 3, height - pad - 2),
        radius=radius, outline=(42, 229, 255, 135), width=max(2, pad // 2),
    )
    plate.alpha_composite(chroma.filter(ImageFilter.GaussianBlur(max(1, pad // 3))))

    body = Image.new("RGBA", plate.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(body, "RGBA")
    draw.rounded_rectangle(
        (pad, pad, width - pad, height - pad), radius=radius,
        fill=(8, 20, 36, 224), outline=(59, 205, 255, 230),
        width=max(3, round(frame_height * .0022)),
    )
    inner = max(7, pad * 2)
    draw.rounded_rectangle(
        (inner, inner, width - inner, height - inner),
        radius=max(6, radius - inner // 2),
        outline=(135, 231, 255, 105), width=max(1, pad // 3),
    )
    tick = max(10, round(height * .11))
    line = max(2, round(frame_height * .0015))
    for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        x = inner if sx == 1 else width - inner
        y = inner if sy == 1 else height - inner
        draw.line((x, y, x + sx * tick, y), fill=(212, 249, 255, 205), width=line)
        draw.line((x, y, x, y + sy * tick), fill=(212, 249, 255, 205), width=line)
    rail_y = max(3, inner // 2)
    draw.line((width * .22, rail_y, width * .78, rail_y), fill=(75, 212, 255, 150), width=line)
    for fraction in (.23, .38, .62, .77):
        x = round(width * fraction)
        draw.ellipse((x - line * 2, rail_y - line * 2, x + line * 2, rail_y + line * 2),
                     fill=(119, 240, 255, 220))
    for y in range(inner + 2, height - inner, max(5, round(frame_height * .0035))):
        draw.line((inner, y, width - inner, y), fill=(122, 218, 255, 12), width=1)
    glow = body.filter(ImageFilter.GaussianBlur(max(4, round(frame_height * .006))))
    glow.putalpha(glow.getchannel("A").point(lambda value: round(value * .42)))
    plate.alpha_composite(glow)
    plate.alpha_composite(body)
    plate.alpha_composite(value, ((width - value.width) // 2, (height - value.height) // 2))
    return plate


def _identity_plate(text: str, frame_height: int, max_width: int,
                    accent: tuple[int, int, int],
                    font_scale: float = .030) -> Image.Image:
    """Render a compact photographed-subject ID rail without truncation."""
    prefix, separator, name = text.partition("｜")
    prefix_text = prefix if separator else ""
    name_text = name if separator else prefix
    padding = max(13, round(frame_height * .008))
    gap = max(8, round(frame_height * .005))
    font_px = max(24, round(frame_height * font_scale))
    while True:
        prefix_font = _font(prefix, max(18, round(font_px * .72)))
        name_font = _font(name or prefix, font_px)
        prefix_box = prefix_font.getbbox(prefix_text) if prefix_text else (0, 0, 0, 0)
        name_box = name_font.getbbox(name_text)
        prefix_width = prefix_box[2] - prefix_box[0]
        name_width = name_box[2] - name_box[0]
        required = padding * 2 + prefix_width + (gap if prefix_text else 0) + name_width
        if required <= max_width or font_px <= 24:
            break
        font_px -= 2
    text_height = max(prefix_box[3] - prefix_box[1], name_box[3] - name_box[1])
    width = min(max_width, required)
    height = max(round(frame_height * .052), text_height + padding)
    radius = max(12, round(height * .28))
    plate = Image.new("RGBA", (width + 16, height + 16), (0, 0, 0, 0))
    body = Image.new("RGBA", plate.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(body, "RGBA")
    box = (8, 8, width + 7, height + 7)
    draw.rounded_rectangle(
        box, radius=radius, fill=(7, 12, 20, 205),
        outline=(235, 247, 255, 82), width=max(1, round(frame_height * .0012)),
    )
    accent_width = max(4, round(frame_height * .0030))
    draw.rounded_rectangle(
        (8, 8, 8 + accent_width, height + 7),
        radius=max(2, accent_width // 2), fill=(*accent, 245),
    )
    draw.line((8 + radius, 9, width + 7 - radius, 9),
              fill=(255, 255, 255, 92), width=max(1, round(frame_height * .0009)))
    text_x = 8 + padding
    baseline = 8 + (height - text_height) // 2
    if prefix_text:
        prefix_y = baseline - prefix_box[1]
        draw.text((text_x, prefix_y), prefix_text, font=prefix_font, fill=(*accent, 245))
        text_x += prefix_width + gap
        divider_x = text_x - gap // 2
        draw.line((divider_x, 8 + height * .28, divider_x, 8 + height * .72),
                  fill=(225, 239, 247, 82), width=max(1, round(frame_height * .001)))
    name_y = baseline - name_box[1]
    draw.text((text_x, name_y), name_text, font=name_font, fill=(248, 251, 253, 250))
    shadow = body.filter(ImageFilter.GaussianBlur(max(4, round(frame_height * .004))))
    shadow.putalpha(shadow.getchannel("A").point(lambda value: round(value * .28)))
    plate.alpha_composite(shadow, (0, 3))
    plate.alpha_composite(body)
    return plate


def build_track_plate(config: dict[str, Any], frame_width: int,
                      frame_height: int) -> Image.Image:
    """Build the immutable base plate for one validated tracked label."""
    text = str(config["text"])
    profile = str(config.get("profile", "neon_value_green"))
    font_scale = float(config.get("font_scale", TEXT_PROFILES[profile]["font_scale"]))
    maximum = round(frame_width * float(config.get("max_width", .64)))
    style = str(config.get("style", "typography"))
    if style == "telemetry_callout":
        return _telemetry_plate(text, frame_height, maximum)
    if style == "identity_callout":
        accent = tuple(int(value) for value in config.get("pointer_color", [66, 215, 255]))
        return _identity_plate(text, frame_height, maximum, accent, font_scale=font_scale)
    return render_text_plate(text, profile, round(frame_height * font_scale), max_width=maximum)


def _animated_plate(state: TrackPresentationState, source_time: float,
                    opacity: float) -> tuple[Image.Image, float, float, str]:
    start, end = float(state.config.get("start", 0)), float(state.config["end"])
    style = str(state.config.get("style", "typography"))
    assert state.base_plate is not None
    if style == "identity_callout":
        plate = animate_identity_plate(state.base_plate, source_time - start, end - start)
    else:
        plate = animate_text_plate(
            state.base_plate, source_time - start, end - start,
            str(state.config.get("profile", "neon_value_green")),
        )
    if opacity < 1:
        plate.putalpha(plate.getchannel("A").point(lambda value: round(value * opacity)))
    return plate, start, end, style


def _place_track_plate(state: TrackPresentationState, plate: Image.Image,
                       style: str) -> tuple[int, int, str]:
    assert state.smooth_box is not None
    x, y, width, height = state.smooth_box
    anchor = str(state.config.get("anchor", "top"))
    gap = round(state.frame_height * float(state.config.get("gap", .018)))
    placed_side = anchor
    if style == "telemetry_callout":
        offset = state.config.get("panel_offset", [-.16, -.13])
        offset_x = float(offset[0]) * state.frame_width if abs(float(offset[0])) <= 1.5 else float(offset[0])
        offset_y = float(offset[1]) * state.frame_height if abs(float(offset[1])) <= 1.5 else float(offset[1])
        plate_x = x + width * .5 + offset_x - plate.width * .5
        plate_y = y + height * .5 + offset_y - plate.height * .5
    elif style == "identity_callout":
        margin = round(state.frame_height * .018)
        if state.config.get("panel_offset") is not None:
            offset = state.config["panel_offset"]
            offset_x = float(offset[0]) * state.frame_width if abs(float(offset[0])) <= 1.5 else float(offset[0])
            offset_y = float(offset[1]) * state.frame_height if abs(float(offset[1])) <= 1.5 else float(offset[1])
            plate_x = x + width * .5 + offset_x - plate.width * .5
            plate_y = y + height * .5 + offset_y - plate.height * .5
            placed_side = "offset"
        elif str(state.config.get("layout_lane", "")) == "upper_rail":
            plate_x = x + width * .5 - plate.width * .5
            plate_y = min(state.frame_height * .22, y - plate.height - gap * 2)
            placed_side = "top"
        else:
            plate_x, plate_y, placed_side = _identity_callout_position(
                subject=(x, y, width, height), plate_size=plate.size, preferred=anchor,
                gap=gap, margin=margin, frame_size=(state.frame_width, state.frame_height),
            )
    elif anchor == "bottom":
        plate_x, plate_y = x + width / 2 - plate.width / 2, y + height + gap
    elif anchor == "left":
        plate_x, plate_y = x - plate.width - gap, y + height / 2 - plate.height / 2
    elif anchor == "right":
        plate_x, plate_y = x + width + gap, y + height / 2 - plate.height / 2
    else:
        plate_x, plate_y = x + width / 2 - plate.width / 2, y - plate.height - gap
    margin = round(state.frame_height * .018)
    plate_x = min(max(margin, round(plate_x)), state.frame_width - plate.width - margin)
    plate_y = min(max(margin, round(plate_y)), state.frame_height - plate.height - margin)
    return plate_x, plate_y, placed_side


def _draw_telemetry_connector(state: TrackPresentationState, overlay: Image.Image,
                              plate: Image.Image, plate_x: int, plate_y: int,
                              source_time: float, start: float) -> None:
    assert state.smooth_box is not None
    x, y, width, height = state.smooth_box
    target = state.config.get("pointer_target", [.5, .5])
    target_x = round(x + width * float(target[0]))
    target_y = round(y + height * float(target[1]))
    attach_left = target_x < plate_x + plate.width / 2
    source_x = plate_x if attach_left else plate_x + plate.width
    source_y = plate_y + plate.height * .72
    elbow_x = round(source_x + (target_x - source_x) * .62)
    local_time = max(0.0, source_time - start)
    reveal = min(1.0, local_time / max(.08, float(state.config.get("connector_reveal", .22))))
    reveal = 1.0 - (1.0 - reveal) ** 3
    points = [(round(source_x), round(source_y)), (elbow_x, round(source_y)), (target_x, target_y)]
    points[-1] = (
        round(elbow_x + (target_x - elbow_x) * reveal),
        round(source_y + (target_y - source_y) * reveal),
    )
    connector = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(connector, "RGBA")
    thickness = max(3, round(state.frame_height * .0032))
    for offset, color in ((-3, (255, 46, 93, 95)), (3, (34, 225, 255, 115))):
        shifted = [(point_x + offset, point_y) for point_x, point_y in points]
        draw.line(shifted, fill=color, width=max(2, thickness // 2), joint="curve")
    draw.line(points, fill=(55, 205, 255, 245), width=thickness, joint="curve")
    draw.line(points, fill=(220, 251, 255, 225), width=max(1, thickness // 3), joint="curve")
    endpoint = points[-1]
    dot = max(6, round(state.frame_height * .008))
    draw.ellipse((endpoint[0] - dot, endpoint[1] - dot,
                  endpoint[0] + dot, endpoint[1] + dot),
                 fill=(67, 219, 255, 245), outline=(240, 255, 255, 245),
                 width=max(2, thickness // 2))
    connector_glow = connector.filter(ImageFilter.GaussianBlur(max(5, dot)))
    connector_glow.putalpha(connector_glow.getchannel("A").point(lambda value: round(value * .48)))
    overlay.alpha_composite(connector_glow)
    overlay.alpha_composite(connector)


def _identity_target(state: TrackPresentationState) -> tuple[int, int]:
    assert state.smooth_box is not None
    x, y, width, height = state.smooth_box
    target = state.config.get("pointer_target", [.5, .5])
    return round(x + width * float(target[0])), round(y + height * float(target[1]))


def _draw_identity_edge_pin(state: TrackPresentationState, overlay: Image.Image,
                            plate: Image.Image, plate_x: int, plate_y: int,
                            placed_side: str, source_time: float, start: float) -> None:
    assert state.smooth_box is not None
    x, y, width, height = state.smooth_box
    if placed_side == "left":
        source_x, source_y = plate_x + plate.width, round(plate_y + plate.height * .54)
        target_x, target_y = round(x + width * .04), round(y + height * .50)
    elif placed_side == "right":
        source_x, source_y = plate_x, round(plate_y + plate.height * .54)
        target_x, target_y = round(x + width * .96), round(y + height * .50)
    elif placed_side == "top":
        source_x, source_y = round(plate_x + plate.width * .50), plate_y + plate.height
        target_x, target_y = round(x + width * .50), round(y + height * .04)
    else:
        source_x, source_y = round(plate_x + plate.width * .50), plate_y
        target_x, target_y = round(x + width * .50), round(y + height * .96)
    local_time = max(0.0, source_time - start)
    reveal = min(1.0, local_time / max(.10, float(state.config.get("connector_reveal", .20))))
    reveal = reveal * reveal * (3.0 - 2.0 * reveal)
    animated = (
        round(source_x + (target_x - source_x) * reveal),
        round(source_y + (target_y - source_y) * reveal),
    )
    pin = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    pin_draw = ImageDraw.Draw(pin, "RGBA")
    color = tuple(int(value) for value in state.config.get("pointer_color", [66, 215, 255]))
    line = max(2, round(state.frame_height * .00135))
    pin_draw.line((round(source_x), round(source_y), *animated), fill=(*color, 138), width=line)
    dot = max(3, round(state.frame_height * .0030))
    pin_draw.ellipse((animated[0] - dot, animated[1] - dot,
                      animated[0] + dot, animated[1] + dot),
                     fill=(244, 253, 255, 228), outline=(*color, 208), width=max(1, line))
    pin_glow = pin.filter(ImageFilter.GaussianBlur(max(2, line * 2)))
    pin_glow.putalpha(pin_glow.getchannel("A").point(lambda value: round(value * .16)))
    overlay.alpha_composite(pin_glow)
    overlay.alpha_composite(pin)
    overlay.alpha_composite(plate, (plate_x, plate_y))


def _draw_identity_marker(state: TrackPresentationState, overlay: Image.Image,
                          plate: Image.Image, plate_x: int, plate_y: int) -> None:
    target_x, target_y = _identity_target(state)
    marker = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    marker_draw = ImageDraw.Draw(marker, "RGBA")
    color = tuple(int(value) for value in state.config.get("pointer_color", [66, 215, 255]))
    outer = max(8, round(state.frame_height * .0080))
    inner = max(3, round(state.frame_height * .0032))
    line = max(2, round(state.frame_height * .0016))
    marker_draw.ellipse((target_x - outer, target_y - outer,
                         target_x + outer, target_y + outer),
                        outline=(*color, 205), width=line)
    marker_draw.ellipse((target_x - inner, target_y - inner,
                         target_x + inner, target_y + inner),
                        fill=(248, 253, 255, 235))
    marker_glow = marker.filter(ImageFilter.GaussianBlur(max(3, outer // 2)))
    marker_glow.putalpha(marker_glow.getchannel("A").point(lambda value: round(value * .26)))
    overlay.alpha_composite(marker_glow)
    overlay.alpha_composite(marker)
    overlay.alpha_composite(plate, (plate_x, plate_y))


def _draw_identity_elbow(state: TrackPresentationState, overlay: Image.Image,
                         plate: Image.Image, plate_x: int, plate_y: int,
                         placed_side: str, source_time: float, start: float) -> None:
    target_x, target_y = _identity_target(state)
    if placed_side in {"top", "bottom"}:
        source_x = round(plate_x + plate.width * .5)
        source_y = plate_y + plate.height if placed_side == "top" else plate_y
        vertical = max(round(state.frame_height * .016),
                       min(round(state.frame_height * .048), abs(target_y - source_y) * .48))
        elbow = (source_x, round(source_y + vertical if placed_side == "top" else source_y - vertical))
    else:
        source_x = plate_x + plate.width if placed_side == "left" else plate_x
        source_y = round(plate_y + plate.height * .56)
        horizontal = max(round(state.frame_height * .016),
                         min(round(state.frame_height * .048), abs(target_x - source_x) * .48))
        elbow = (round(source_x + horizontal if placed_side == "left" else source_x - horizontal), source_y)
    points = [(round(source_x), round(source_y)), elbow, (target_x, target_y)]
    local_time = max(0.0, source_time - start)
    reveal = min(1.0, local_time / max(.08, float(state.config.get("connector_reveal", .16))))
    reveal = 1.0 - (1.0 - reveal) ** 3
    points[-1] = (
        round(elbow[0] + (target_x - elbow[0]) * reveal),
        round(elbow[1] + (target_y - elbow[1]) * reveal),
    )
    connector = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(connector, "RGBA")
    color = tuple(int(value) for value in state.config.get("pointer_color", [66, 215, 255]))
    thickness = max(2, round(state.frame_height * .0022))
    draw.line(points, fill=(*color, 225), width=thickness, joint="curve")
    draw.line(points, fill=(246, 253, 255, 180), width=max(1, thickness // 2), joint="curve")
    endpoint = points[-1]
    dot = max(4, round(state.frame_height * .0055))
    draw.ellipse((endpoint[0] - dot, endpoint[1] - dot,
                  endpoint[0] + dot, endpoint[1] + dot),
                 fill=(*color, 245), outline=(255, 255, 255, 235),
                 width=max(1, thickness // 2))
    glow = connector.filter(ImageFilter.GaussianBlur(max(3, dot)))
    glow.putalpha(glow.getchannel("A").point(lambda value: round(value * .30)))
    overlay.alpha_composite(glow)
    overlay.alpha_composite(connector)


def _draw_identity_connector(state: TrackPresentationState, overlay: Image.Image,
                             plate: Image.Image, plate_x: int, plate_y: int,
                             placed_side: str, source_time: float, start: float) -> bool:
    """Draw one identity connector; return True when it also placed the plate."""
    connector_style = str(state.config.get("connector_style", "minimal_elbow"))
    if connector_style == "floating_tag":
        overlay.alpha_composite(plate, (plate_x, plate_y))
        return True
    if connector_style == "edge_pin":
        _draw_identity_edge_pin(
            state, overlay, plate, plate_x, plate_y, placed_side, source_time, start,
        )
        return True
    if connector_style == "marker_only":
        _draw_identity_marker(state, overlay, plate, plate_x, plate_y)
        return True
    _draw_identity_elbow(
        state, overlay, plate, plate_x, plate_y, placed_side, source_time, start,
    )
    return False


def _draw_arrow(state: TrackPresentationState, overlay: Image.Image,
                plate: Image.Image, plate_x: int, plate_y: int,
                source_time: float, start: float) -> None:
    if state.config.get("pointer") != "arrow":
        return
    assert state.smooth_box is not None
    x, y, width, height = state.smooth_box
    gap = round(state.frame_height * float(state.config.get("gap", .018)))
    color = tuple(state.config.get("pointer_color", [255, 38, 45]))
    start_point = (plate_x + plate.width // 2, plate_y + plate.height - max(4, gap // 3))
    target = state.config.get("pointer_target", [.5, .32])
    end_point = (round(x + width * float(target[0])), round(y + height * float(target[1])))
    thickness = max(5, round(state.frame_height * .008))
    local_time = max(0.0, source_time - start)
    reveal = min(1.0, local_time / max(.08, float(state.config.get("pointer_reveal", .18))))
    reveal = 1.0 - (1.0 - reveal) ** 3
    animated_end = (
        round(start_point[0] + (end_point[0] - start_point[0]) * reveal),
        round(start_point[1] + (end_point[1] - start_point[1]) * reveal),
    )
    arrow = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(arrow, "RGBA")
    draw.line((start_point, animated_end), fill=(*color, 255), width=thickness)
    draw.line((start_point, animated_end), fill=(255, 255, 255, 205), width=max(1, thickness // 4))
    angle = math.atan2(animated_end[1] - start_point[1], animated_end[0] - start_point[0])
    head = max(12, round(state.frame_height * .025))
    points = [animated_end]
    for delta in (2.55, -2.55):
        points.append((
            round(animated_end[0] + math.cos(angle + delta) * head),
            round(animated_end[1] + math.sin(angle + delta) * head),
        ))
    draw.polygon(points, fill=(*color, 255))
    if reveal > .08:
        glow = arrow.filter(ImageFilter.GaussianBlur(max(4, thickness)))
        glow.putalpha(glow.getchannel("A").point(lambda value: round(value * .54)))
        overlay.alpha_composite(glow)
        overlay.alpha_composite(arrow)


def draw_track_runtime(state: TrackPresentationState, overlay: Image.Image,
                       source_time: float, opacity: float) -> None:
    """Present one tracked runtime without owning or mutating tracking state."""
    if not state.smooth_box or state.base_plate is None or opacity <= 0:
        return
    plate, start, _end, style = _animated_plate(state, source_time, opacity)
    plate_x, plate_y, placed_side = _place_track_plate(state, plate, style)
    if style == "telemetry_callout":
        _draw_telemetry_connector(state, overlay, plate, plate_x, plate_y, source_time, start)
    if style == "identity_callout" and _draw_identity_connector(
            state, overlay, plate, plate_x, plate_y, placed_side, source_time, start):
        return
    _draw_arrow(state, overlay, plate, plate_x, plate_y, source_time, start)
    overlay.alpha_composite(plate, (plate_x, plate_y))


def _position_pixels(values: list[float], width: int, height: int) -> tuple[float, float]:
    x, y = float(values[0]), float(values[1])
    if max(abs(x), abs(y)) <= 1.5:
        return x * width, y * height
    return x, y


def _lock_center(effect: dict[str, Any], source_time: float,
                 width: int, height: int) -> tuple[float, float]:
    rows = list(effect.get("keyframes") or [])
    if not rows:
        return _position_pixels(effect.get("center", [.5, .53]), width, height)
    rows.sort(key=lambda row: float(row["time"]))
    if source_time <= float(rows[0]["time"]):
        return _position_pixels(rows[0]["center"], width, height)
    if source_time >= float(rows[-1]["time"]):
        return _position_pixels(rows[-1]["center"], width, height)
    for left, right in zip(rows, rows[1:]):
        start, end = float(left["time"]), float(right["time"])
        if start <= source_time <= end:
            progress = (source_time - start) / max(.0001, end - start)
            progress = progress * progress * (3.0 - 2.0 * progress)
            x1, y1 = _position_pixels(left["center"], width, height)
            x2, y2 = _position_pixels(right["center"], width, height)
            return x1 + (x2 - x1) * progress, y1 + (y2 - y1) * progress
    return _position_pixels(rows[-1]["center"], width, height)


def _draw_lock_effect(overlay: Image.Image, effect: dict[str, Any],
                      source_time: float, width: int, height: int) -> None:
    """Draw a restrained arena/object lock overlay; never a transition card."""
    start, end = float(effect.get("start", 0)), float(effect.get("end", 0))
    if not start <= source_time < end:
        return
    center_x, center_y = _lock_center(effect, source_time, width, height)
    raw_radius = float(effect.get("radius", .16))
    radius = raw_radius * min(width, height) if raw_radius <= 1.5 else raw_radius
    local_time = source_time - start
    radius *= 1.0 + .025 * math.sin(local_time * math.tau * 1.7)
    color = tuple(int(value) for value in effect.get("color", [56, 215, 255]))
    line = max(3, round(height * float(effect.get("line_width", .0035))))
    layer = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    box = (round(center_x - radius), round(center_y - radius),
           round(center_x + radius), round(center_y + radius))
    angle = (local_time * float(effect.get("rotation_speed", 82))) % 360
    draw.ellipse(box, outline=(*color, 58), width=max(2, line // 2))
    for offset in (0, 180):
        draw.arc(box, start=angle + offset, end=angle + offset + 58,
                 fill=(*color, 235), width=line)
    bracket = radius * float(effect.get("bracket_length", .24))
    gap = radius * float(effect.get("bracket_gap", .88))
    for side_x, side_y in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        x, y = center_x + side_x * gap, center_y + side_y * gap
        draw.line((x, y, x - side_x * bracket, y), fill=(*color, 220), width=line)
        draw.line((x, y, x, y - side_y * bracket), fill=(*color, 220), width=line)
    glow = layer.filter(ImageFilter.GaussianBlur(max(3, round(height * .006))))
    glow.putalpha(glow.getchannel("A").point(lambda value: round(value * .52)))
    overlay.alpha_composite(glow)
    overlay.alpha_composite(layer)


def _alpha_matte(effect: dict[str, Any], width: int, height: int,
                 frame_box: tuple[int, int, int, int],
                 frame_size: tuple[int, int]) -> Image.Image:
    raw = Image.open(str(effect["matte_path"]))
    source = raw.convert("RGBA")
    alpha = source.getchannel("A") if "A" in raw.getbands() else raw.convert("L")
    if source.size == frame_size:
        left, top, right, bottom = frame_box
        alpha = alpha.crop((left, top, right, bottom))
    if alpha.size != (width, height):
        alpha = alpha.resize((width, height), Image.Resampling.LANCZOS)
    return alpha


def _sequence_matte(effect: dict[str, Any], source_time: float,
                    width: int, height: int,
                    frame_box: tuple[int, int, int, int],
                    frame_size: tuple[int, int]) -> Image.Image:
    fps = float(effect["matte_sequence_fps"])
    sequence_start = float(effect.get("matte_sequence_start", effect.get("start", 0)))
    frame_index = max(0, int(math.floor((source_time - sequence_start) * fps + 1e-6)))
    prefix = str(effect.get("matte_sequence_prefix", "frame_"))
    digits = max(1, int(effect.get("matte_sequence_digits", 6)))
    extension = str(effect.get("matte_sequence_extension", ".png"))
    if not extension.startswith("."):
        extension = "." + extension
    path = Path(str(effect["matte_sequence_dir"])) / f"{prefix}{frame_index:0{digits}d}{extension}"
    if not path.is_file():
        raise RuntimeError(f"missing required roto matte frame: {path}")
    local_effect = dict(effect)
    local_effect["matte_path"] = str(path)
    return _alpha_matte(local_effect, width, height, frame_box, frame_size)


def _verified_sheen_matte(effect: dict[str, Any], width: int, height: int,
                          frame_box: tuple[int, int, int, int],
                          frame_size: tuple[int, int],
                          source_time: float) -> Image.Image:
    shape = str(effect.get("shape", "ellipse"))
    if shape == "alpha":
        matte = _alpha_matte(effect, width, height, frame_box, frame_size)
    elif shape == "sequence":
        matte = _sequence_matte(effect, source_time, width, height, frame_box, frame_size)
    else:
        matte = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(matte)
        inset = max(0.0, min(.35, float(effect.get("matte_inset", .025))))
        box = (round(width * inset), round(height * inset),
               round(width * (1 - inset)), round(height * (1 - inset)))
        if shape == "polygon":
            points = [(round(float(x) * width), round(float(y) * height))
                      for x, y in effect.get("polygon", [])]
            draw.polygon(points, fill=255)
        elif shape == "rectangle":
            radius = round(min(width, height) * float(effect.get("corner_radius", .08)))
            draw.rounded_rectangle(box, radius=radius, fill=255)
        else:
            draw.ellipse(box, fill=255)
    feather = max(1, round(min(width, height) * float(effect.get("matte_feather", .018))))
    return matte.filter(ImageFilter.GaussianBlur(feather))


def _subject_blackout(effect: dict[str, Any], frame: np.ndarray | None,
                      matte_alpha: np.ndarray, projection: np.ndarray,
                      center: float, sigma: float,
                      crop_box: tuple[int, int, int, int]) -> Image.Image | None:
    if str(effect.get("reveal_mode", "sheen_only")) != "black_to_color":
        return None
    left, top, width, height = crop_box
    softness = max(.08, min(1.2, float(effect.get("reveal_softness", .42))))
    edge_sigma = max(1.0, sigma * softness)
    exponent = np.clip((projection - center) / edge_sigma, -24.0, 24.0)
    revealed = 1.0 / (1.0 + np.exp(exponent))
    opacity = max(0.0, min(1.0, float(effect.get("blackout_opacity", 1.0))))
    alpha = np.clip((1.0 - revealed) * matte_alpha * opacity * 255.0, 0, 255).astype(np.uint8)
    if frame is None:
        blackout = Image.new("RGBA", (width, height), (3, 7, 12, 0))
        blackout.putalpha(Image.fromarray(alpha))
        return blackout
    crop = frame[top:top + height, left:left + width]
    grey = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    detail = np.power(grey, .78)
    dark_rgb = np.stack((detail * 20.0, detail * 25.0, detail * 31.0), axis=-1)
    blackout_rgba = np.zeros((height, width, 4), dtype=np.uint8)
    blackout_rgba[..., :3] = np.clip(dark_rgb, 0, 42).astype(np.uint8)[..., ::-1]
    blackout_rgba[..., 3] = alpha
    return Image.fromarray(blackout_rgba, "RGBA")


def _sheen_local_layer(effect: dict[str, Any], material: dict[str, float],
                       band: np.ndarray, optical_core: np.ndarray,
                       matte_alpha: np.ndarray) -> Image.Image:
    alpha = (band * .72 + optical_core * .28) * matte_alpha
    opacity = max(0.0, min(1.0, float(effect.get("opacity", material["opacity"]))))
    core = max(.01, min(1.0, float(effect.get("core", material["core"]))))
    alpha = np.clip(alpha * opacity * core * 255.0, 0, 255).astype(np.uint8)
    warm = np.array(effect.get("warm_color", [255, 246, 220]), dtype=np.float32)
    cool = np.array(effect.get("cool_color", [175, 226, 255]), dtype=np.float32)
    warm_mix = np.clip(optical_core[..., None], 0.0, 1.0)
    rgb = cool[None, None, :] * (1.0 - warm_mix) + warm[None, None, :] * warm_mix
    rgba = np.zeros((*matte_alpha.shape, 4), dtype=np.uint8)
    rgba[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    rgba[..., 3] = alpha
    return Image.fromarray(rgba)


def _draw_sheen_shoulders(overlay: Image.Image, effect: dict[str, Any],
                          material: dict[str, float], projection: np.ndarray,
                          center: float, sigma: float, band: np.ndarray,
                          matte_alpha: np.ndarray, left: int, top: int) -> None:
    contrast = max(0.0, min(.45, float(effect.get("contrast", material["contrast"]))))
    if not contrast:
        return
    shoulder_distance = sigma * float(effect.get("shoulder_distance", 1.42))
    shoulder_sigma = sigma * float(effect.get("shoulder_width", .72))
    shoulder = (
        np.exp(-.5 * ((projection - (center - shoulder_distance)) / shoulder_sigma) ** 2)
        + np.exp(-.5 * ((projection - (center + shoulder_distance)) / shoulder_sigma) ** 2)
    )
    shoulder *= np.clip(1.0 - band * .82, 0.0, 1.0)
    alpha = np.clip(shoulder * matte_alpha * contrast * 255.0, 0, 255).astype(np.uint8)
    shadow = Image.new("RGBA", (matte_alpha.shape[1], matte_alpha.shape[0]), (4, 8, 14, 0))
    shadow.putalpha(Image.fromarray(alpha))
    overlay.alpha_composite(shadow, (left, top))


def _draw_mask_sheen(overlay: Image.Image, effect: dict[str, Any],
                     source_time: float, width: int, height: int,
                     frame: np.ndarray | None = None, *,
                     bbox_resolver: Callable[[dict[str, Any], float, int, int],
                                             tuple[float, float, float, float]]) -> None:
    """Sweep a diagonal highlight only inside a verified subject matte."""
    start, end = float(effect.get("start", 0)), float(effect.get("end", 0))
    if not start <= source_time < end:
        return
    x, y, box_width, box_height = bbox_resolver(effect, source_time, width, height)
    left, top = max(0, round(x)), max(0, round(y))
    local_width = max(4, min(width - left, round(box_width)))
    local_height = max(4, min(height - top, round(box_height)))
    if local_width < 4 or local_height < 4:
        return
    frame_box = (left, top, left + local_width, top + local_height)
    matte = _verified_sheen_matte(
        effect, local_width, local_height, frame_box, (width, height), source_time,
    )
    material = SHEEN_MATERIALS[str(effect.get("material_profile", "generic_product"))]
    progress = max(0.0, min(1.0, (source_time - start) / max(.001, end - start)))
    progress = progress * progress * (3.0 - 2.0 * progress)
    grid_y, grid_x = np.mgrid[0:local_height, 0:local_width].astype(np.float32)
    angle = math.radians(float(effect.get("angle", -28.0)))
    projection = grid_x * math.cos(angle) + grid_y * math.sin(angle)
    minimum, maximum = float(projection.min()), float(projection.max())
    travel_pad = (maximum - minimum) * .20
    center = (minimum - travel_pad) + progress * ((maximum - minimum) + travel_pad * 2)
    sigma = max(
        2.0,
        min(local_width, local_height)
        * float(effect.get("band_width", material["band_width"])) * .38,
    )
    band = np.exp(-.5 * ((projection - center) / sigma) ** 2)
    secondary = float(effect.get("secondary", material["secondary"]))
    band += secondary * np.exp(-.5 * ((projection - (center - sigma * 2.15)) / (sigma * .52)) ** 2)
    matte_alpha = np.asarray(matte, dtype=np.float32) / 255.0
    blackout = _subject_blackout(
        effect, frame, matte_alpha, projection, center, sigma,
        (left, top, local_width, local_height),
    )
    if blackout is not None:
        overlay.alpha_composite(blackout, (left, top))
    optical_core = np.exp(-.5 * ((projection - center) / max(1.0, sigma * .20)) ** 2)
    local = _sheen_local_layer(effect, material, band, optical_core, matte_alpha)
    _draw_sheen_shoulders(
        overlay, effect, material, projection, center, sigma, band,
        matte_alpha, left, top,
    )
    glow_radius = max(1, round(min(local_width, local_height)
                               * float(effect.get("glow", material["glow"]))))
    glow = local.filter(ImageFilter.GaussianBlur(glow_radius))
    glow_alpha = np.asarray(glow.getchannel("A"), dtype=np.float32)
    glow.putalpha(Image.fromarray(
        np.clip(glow_alpha * matte_alpha * .45, 0, 255).astype(np.uint8)
    ))
    overlay.alpha_composite(glow, (left, top))
    overlay.alpha_composite(local, (left, top))
