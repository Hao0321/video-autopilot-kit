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


from tracked_subject_effects import (
    SHEEN_MATERIALS,
    _position_pixels,
    _lock_center,
    _draw_lock_effect,
    _alpha_matte,
    _sequence_matte,
    _verified_sheen_matte,
    _subject_blackout,
    _sheen_local_layer,
    _draw_sheen_shoulders,
    _draw_mask_sheen,
)


from tracked_connectors import (
    TrackPresentationState,
    _identity_target,
    _draw_identity_edge_pin,
    _draw_identity_marker,
    _draw_identity_elbow,
    _draw_identity_connector,
    _draw_arrow,
)


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


