"""Tracked connectors; one implementation behind the compatibility facade."""
from __future__ import annotations
from typing import Any, Protocol

import math
from PIL import Image, ImageDraw, ImageFilter


class TrackPresentationState(Protocol):
    """Read-only state needed to present one tracked label."""

    config: dict[str, Any]
    frame_width: int
    frame_height: int
    smooth_box: tuple[float, float, float, float] | None
    base_plate: Image.Image | None

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
