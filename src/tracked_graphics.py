# -*- coding: utf-8 -*-
"""Tracked kinetic typography and challenge-ledger HUD renderer.

This module turns a verified initial bounding box into a real frame-by-frame
track, attaches editable Chinese/English/numeric typography to the subject and
optionally renders a stateful top-left challenge ledger.  It is an overlay
renderer, never a transition generator.

CLI examples::

    python tracked_graphics.py validate spec.json
    python tracked_graphics.py render spec.json --output tracked.mp4
    python tracked_graphics.py demo --out-dir _runtime/tracked-graphics-demo
    python tracked_graphics.py selftest
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from challenge_hud import render_challenge_hud
from tracked_typography import (
    CURRENCY_RE,
    TEXT_PROFILES,
    animate_text_plate,
    font as _font,
    render_text_plate,
)
from tracked_graphics_validation import validate_spec as _validate_tracked_spec
from visual_master import analyze_media

SHEEN_MATERIALS = {
    # A subject sheen must read as a material event on the object, not as a
    # pale full-frame wash.  ``contrast`` adds two narrow, object-clipped dark
    # shoulders around the bright core.  This keeps a white battle top legible
    # while making the diagonal specular pass visibly stronger.
    "battle_top": {
        "opacity": .92, "band_width": .105, "glow": .024,
        "secondary": .34, "core": .98, "contrast": .24,
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

MEASURED_VALUE_RE = __import__("re").compile(
    r"(?:\d[\d,.]*\s*(?:mph|km/?h|kph|m/?s|fps|kg|g|cm|mm|m|秒|公里|公尺|公斤))",
    __import__("re").I,
)


def _telemetry_plate(text: str, frame_height: int, max_width: int) -> Image.Image:
    """Render an editable cinematic telemetry plate, not a flat sticker."""
    font_px = max(38, round(frame_height * .064))
    value = render_text_plate(text, "price_white", font_px, max_width=round(max_width * .72))
    width = min(max_width, max(value.width + round(frame_height * .085), round(frame_height * .24)))
    height = max(value.height + round(frame_height * .040), round(frame_height * .105))
    pad = max(4, round(frame_height * .007))
    radius = max(12, round(height * .15))
    plate = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # Restrained chromatic registration offsets give a fast optical/glitch
    # accent without turning the entire plate into a cheap RGB split.
    chroma = Image.new("RGBA", plate.size, (0, 0, 0, 0))
    cd = ImageDraw.Draw(chroma, "RGBA")
    cd.rounded_rectangle((pad - 3, pad + 2, width - pad - 3, height - pad + 2),
                         radius=radius, outline=(255, 53, 96, 115), width=max(2, pad // 2))
    cd.rounded_rectangle((pad + 3, pad - 2, width - pad + 3, height - pad - 2),
                         radius=radius, outline=(42, 229, 255, 135), width=max(2, pad // 2))
    plate.alpha_composite(chroma.filter(ImageFilter.GaussianBlur(max(1, pad // 3))))

    body = Image.new("RGBA", plate.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(body, "RGBA")
    draw.rounded_rectangle((pad, pad, width - pad, height - pad), radius=radius,
                           fill=(8, 20, 36, 224), outline=(59, 205, 255, 230),
                           width=max(3, round(frame_height * .0022)))
    inner = max(7, pad * 2)
    draw.rounded_rectangle((inner, inner, width - inner, height - inner),
                           radius=max(6, radius - inner // 2),
                           outline=(135, 231, 255, 105), width=max(1, pad // 3))
    # Corner locks and upper telemetry rail.
    tick = max(10, round(height * .11))
    line = max(2, round(frame_height * .0015))
    for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        x = inner if sx == 1 else width - inner
        y = inner if sy == 1 else height - inner
        draw.line((x, y, x + sx * tick, y), fill=(212, 249, 255, 205), width=line)
        draw.line((x, y, x, y + sy * tick), fill=(212, 249, 255, 205), width=line)
    rail_y = max(3, inner // 2)
    draw.line((width * .22, rail_y, width * .78, rail_y), fill=(75, 212, 255, 150), width=line)
    for frac in (.23, .38, .62, .77):
        x = round(width * frac)
        draw.ellipse((x - line * 2, rail_y - line * 2, x + line * 2, rail_y + line * 2),
                     fill=(119, 240, 255, 220))
    # Fine scan texture lives inside the plate, not over the footage.
    for y in range(inner + 2, height - inner, max(5, round(frame_height * .0035))):
        draw.line((inner, y, width - inner, y), fill=(122, 218, 255, 12), width=1)
    glow = body.filter(ImageFilter.GaussianBlur(max(4, round(frame_height * .006))))
    glow.putalpha(glow.getchannel("A").point(lambda value: round(value * .42)))
    plate.alpha_composite(glow)
    plate.alpha_composite(body)
    plate.alpha_composite(value, ((width - value.width) // 2, (height - value.height) // 2))
    return plate

def _bbox_pixels(values: list[float], width: int, height: int) -> tuple[float, float, float, float]:
    if len(values) != 4:
        raise ValueError("initial_bbox must contain x, y, width, height")
    x, y, w, h = [float(value) for value in values]
    if max(abs(x), abs(y), abs(w), abs(h)) <= 1.5:
        x, y, w, h = x * width, y * height, w * width, h * height
    if w < 4 or h < 4:
        raise ValueError("initial_bbox is too small")
    x, y = max(0.0, x), max(0.0, y)
    return x, y, min(w, width - x), min(h, height - y)


def _new_csrt_tracker():
    if hasattr(cv2, "TrackerCSRT_create"):
        return cv2.TrackerCSRT_create()
    if hasattr(cv2, "legacy") and hasattr(cv2.legacy, "TrackerCSRT_create"):
        return cv2.legacy.TrackerCSRT_create()
    raise RuntimeError("OpenCV CSRT tracker is unavailable")


def _keyframed_bbox(config: dict[str, Any], source_time: float,
                    width: int, height: int) -> tuple[float, float, float, float]:
    """Interpolate an editorially verified object box without tracker drift.

    Keyframes are intended for short product-showcase shots where the editor can
    verify a handful of boxes.  They are deterministic evidence, not invented
    motion, and are safer than asking CSRT to follow a hand or a spinning top.
    """
    rows = list(config.get("keyframes") or [])
    if not rows:
        return _bbox_pixels(config["initial_bbox"], width, height)
    rows.sort(key=lambda row: float(row["time"]))
    if source_time <= float(rows[0]["time"]):
        return _bbox_pixels(rows[0]["bbox"], width, height)
    if source_time >= float(rows[-1]["time"]):
        return _bbox_pixels(rows[-1]["bbox"], width, height)
    for left, right in zip(rows, rows[1:]):
        a, b = float(left["time"]), float(right["time"])
        if a <= source_time <= b:
            progress = (source_time - a) / max(.0001, b - a)
            progress = progress * progress * (3.0 - 2.0 * progress)
            box_a = _bbox_pixels(left["bbox"], width, height)
            box_b = _bbox_pixels(right["bbox"], width, height)
            return tuple(x + (y - x) * progress for x, y in zip(box_a, box_b))
    return _bbox_pixels(rows[-1]["bbox"], width, height)


@dataclass
class TrackRuntime:
    config: dict[str, Any]
    frame_width: int
    frame_height: int
    tracker: Any = None
    initialized: bool = False
    last_box: tuple[float, float, float, float] | None = None
    smooth_box: tuple[float, float, float, float] | None = None
    lost_frames: int = 0
    base_plate: Image.Image | None = None
    records: list[dict[str, Any]] = field(default_factory=list)

    def initialize(self, frame: np.ndarray) -> None:
        mode = str(self.config.get("tracking_mode", "csrt"))
        box = _keyframed_bbox(
            self.config, float(self.config.get("start", 0)), self.frame_width, self.frame_height,
        ) if mode == "keyframes" else _bbox_pixels(
            self.config["initial_bbox"], self.frame_width, self.frame_height,
        )
        if mode == "csrt":
            self.tracker = _new_csrt_tracker()
            initialized = self.tracker.init(frame, tuple(int(round(v)) for v in box))
            if initialized is False:
                raise RuntimeError("CSRT could not initialize track %s" % self.config.get("id", "track"))
        self.initialized = True
        self.last_box = self.smooth_box = box
        text = str(self.config["text"])
        profile = str(self.config.get("profile", "neon_value_green"))
        font_scale = float(self.config.get("font_scale", TEXT_PROFILES[profile]["font_scale"]))
        maximum = round(self.frame_width * float(self.config.get("max_width", .64)))
        if str(self.config.get("style", "typography")) == "telemetry_callout":
            self.base_plate = _telemetry_plate(text, self.frame_height, maximum)
        else:
            self.base_plate = render_text_plate(
                text, profile, round(self.frame_height * font_scale), max_width=maximum,
            )

    def update(self, frame: np.ndarray, source_time: float, *,
               first_frame: bool = False) -> tuple[str, float]:
        if str(self.config.get("tracking_mode", "csrt")) == "keyframes":
            box = _keyframed_bbox(self.config, source_time, self.frame_width, self.frame_height)
            self.last_box = self.smooth_box = box
            return "tracked", 1.0
        if first_frame:
            return "tracked", 1.0
        ok, raw = self.tracker.update(frame)
        if ok:
            raw_box = tuple(float(v) for v in raw)
            # CSRT may keep returning ``ok`` after it has latched onto a hand,
            # background edge, or a crop boundary.  Treat implausible geometry
            # as a lost track instead of letting the callout jump across frame.
            x, y, w, h = raw_box
            plausible = w >= 4 and h >= 4
            edge_slack = float(self.config.get("edge_slack", .10))
            plausible = plausible and x >= -w * edge_slack and y >= -h * edge_slack
            plausible = plausible and x + w <= self.frame_width + w * edge_slack
            plausible = plausible and y + h <= self.frame_height + h * edge_slack
            if plausible and self.last_box is not None:
                lx, ly, lw, lh = self.last_box
                old_center = np.array([lx + lw / 2, ly + lh / 2])
                new_center = np.array([x + w / 2, y + h / 2])
                jump = float(np.linalg.norm(new_center - old_center))
                max_jump = self.frame_height * float(self.config.get("max_center_jump_ratio", .08))
                area_ratio = (w * h) / max(1.0, lw * lh)
                aspect_ratio = (w / h) / max(.001, lw / lh)
                plausible = jump <= max_jump
                plausible = plausible and .68 <= area_ratio <= 1.47
                plausible = plausible and .72 <= aspect_ratio <= 1.39
            if not plausible:
                self.lost_frames += 1
                hold = int(self.config.get("lost_hold_frames", 8))
                if self.lost_frames <= hold:
                    return "hold", max(.2, 1.0 - self.lost_frames / (hold + 1))
                return "hidden", 0.0
            self.last_box = raw_box
            self.lost_frames = 0
            if self.smooth_box is None:
                self.smooth_box = raw_box
            else:
                old_center = np.array([self.smooth_box[0] + self.smooth_box[2] / 2,
                                       self.smooth_box[1] + self.smooth_box[3] / 2])
                new_center = np.array([raw_box[0] + raw_box[2] / 2, raw_box[1] + raw_box[3] / 2])
                distance = float(np.linalg.norm(new_center - old_center))
                base_follow = float(self.config.get("smoothing_follow", .30))
                follow = min(.42, base_follow * 1.25) if distance > self.frame_height * .03 else base_follow
                size_follow = float(self.config.get("smoothing_size_follow", .18))
                self.smooth_box = tuple(
                    old + (new - old) * (follow if index < 2 else size_follow)
                    for index, (old, new) in enumerate(zip(self.smooth_box, raw_box))
                )
            return "tracked", 1.0
        self.lost_frames += 1
        hold = int(self.config.get("lost_hold_frames", 8))
        if self.lost_frames <= hold:
            return "hold", max(.2, 1.0 - self.lost_frames / (hold + 1))
        return "hidden", 0.0

    def active(self, source_time: float) -> bool:
        return float(self.config.get("start", 0)) <= source_time < float(self.config["end"])

    def draw(self, overlay: Image.Image, source_time: float, opacity: float) -> None:
        if not self.smooth_box or self.base_plate is None or opacity <= 0:
            return
        start, end = float(self.config.get("start", 0)), float(self.config["end"])
        plate = animate_text_plate(
            self.base_plate, source_time - start, end - start,
            str(self.config.get("profile", "neon_value_green")),
        )
        if opacity < 1:
            plate.putalpha(plate.getchannel("A").point(lambda value: round(value * opacity)))
        x, y, w, h = self.smooth_box
        style = str(self.config.get("style", "typography"))
        anchor = str(self.config.get("anchor", "top"))
        gap = round(self.frame_height * float(self.config.get("gap", .018)))
        if style == "telemetry_callout":
            offset = self.config.get("panel_offset", [-.16, -.13])
            ox = float(offset[0]) * self.frame_width if abs(float(offset[0])) <= 1.5 else float(offset[0])
            oy = float(offset[1]) * self.frame_height if abs(float(offset[1])) <= 1.5 else float(offset[1])
            px, py = x + w * .5 + ox - plate.width * .5, y + h * .5 + oy - plate.height * .5
        elif anchor == "bottom":
            px, py = x + w / 2 - plate.width / 2, y + h + gap
        elif anchor == "left":
            px, py = x - plate.width - gap, y + h / 2 - plate.height / 2
        elif anchor == "right":
            px, py = x + w + gap, y + h / 2 - plate.height / 2
        else:
            px, py = x + w / 2 - plate.width / 2, y - plate.height - gap
        margin = round(self.frame_height * .018)
        px = min(max(margin, round(px)), self.frame_width - plate.width - margin)
        py = min(max(margin, round(py)), self.frame_height - plate.height - margin)

        if style == "telemetry_callout":
            target = self.config.get("pointer_target", [.5, .5])
            tx, ty = round(x + w * float(target[0])), round(y + h * float(target[1]))
            attach_left = tx < px + plate.width / 2
            sx = px if attach_left else px + plate.width
            sy = py + plate.height * .72
            elbow_x = round(sx + (tx - sx) * .62)
            local_time = max(0.0, source_time - start)
            reveal = min(1.0, local_time / max(.08, float(self.config.get("connector_reveal", .22))))
            reveal = 1.0 - (1.0 - reveal) ** 3
            points = [(round(sx), round(sy)), (elbow_x, round(sy)), (tx, ty)]
            # Animate along the final segment while the panel settles.
            points[-1] = (round(elbow_x + (tx - elbow_x) * reveal),
                          round(sy + (ty - sy) * reveal))
            connector = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(connector, "RGBA")
            thickness = max(3, round(self.frame_height * .0032))
            for offset, color in ((-3, (255, 46, 93, 95)), (3, (34, 225, 255, 115))):
                shifted = [(pxx + offset, pyy) for pxx, pyy in points]
                draw.line(shifted, fill=color, width=max(2, thickness // 2), joint="curve")
            draw.line(points, fill=(55, 205, 255, 245), width=thickness, joint="curve")
            draw.line(points, fill=(220, 251, 255, 225), width=max(1, thickness // 3), joint="curve")
            endpoint = points[-1]
            dot = max(6, round(self.frame_height * .008))
            draw.ellipse((endpoint[0] - dot, endpoint[1] - dot,
                          endpoint[0] + dot, endpoint[1] + dot),
                         fill=(67, 219, 255, 245), outline=(240, 255, 255, 245),
                         width=max(2, thickness // 2))
            connector_glow = connector.filter(ImageFilter.GaussianBlur(max(5, dot)))
            connector_glow.putalpha(connector_glow.getchannel("A").point(lambda value: round(value * .48)))
            overlay.alpha_composite(connector_glow)
            overlay.alpha_composite(connector)

        pointer = self.config.get("pointer")
        if pointer == "arrow":
            color = tuple(self.config.get("pointer_color", [255, 38, 45]))
            start_pt = (px + plate.width // 2, py + plate.height - max(4, gap // 3))
            target = self.config.get("pointer_target", [.5, .32])
            tx, ty = float(target[0]), float(target[1])
            end_pt = (round(x + w * tx), round(y + h * ty))
            thickness = max(5, round(self.frame_height * .008))
            local_time = max(0.0, source_time - start)
            reveal = min(1.0, local_time / max(.08, float(self.config.get("pointer_reveal", .18))))
            reveal = 1.0 - (1.0 - reveal) ** 3
            animated_end = (
                round(start_pt[0] + (end_pt[0] - start_pt[0]) * reveal),
                round(start_pt[1] + (end_pt[1] - start_pt[1]) * reveal),
            )
            arrow = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(arrow, "RGBA")
            draw.line((start_pt, animated_end), fill=(*color, 255), width=thickness)
            # A soft halo and one-pixel white core keep the pointer readable on
            # real footage without turning it into a flat sticker.
            core = max(1, thickness // 4)
            draw.line((start_pt, animated_end), fill=(255, 255, 255, 205), width=core)
            angle = math.atan2(animated_end[1] - start_pt[1], animated_end[0] - start_pt[0])
            head = max(12, round(self.frame_height * .025))
            points = [animated_end]
            for delta in (2.55, -2.55):
                points.append((round(animated_end[0] + math.cos(angle + delta) * head),
                               round(animated_end[1] + math.sin(angle + delta) * head)))
            draw.polygon(points, fill=(*color, 255))
            if reveal > .08:
                glow = arrow.filter(ImageFilter.GaussianBlur(max(4, thickness)))
                glow.putalpha(glow.getchannel("A").point(lambda value: round(value * .54)))
                overlay.alpha_composite(glow)
                overlay.alpha_composite(arrow)
        overlay.alpha_composite(plate, (px, py))


def validate_spec(spec: dict[str, Any]) -> list[str]:
    return _validate_tracked_spec(
        spec,
        text_profiles=TEXT_PROFILES,
        sheen_materials=SHEEN_MATERIALS,
        currency_re=CURRENCY_RE,
        measured_value_re=MEASURED_VALUE_RE,
    )


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
        a, b = float(left["time"]), float(right["time"])
        if a <= source_time <= b:
            p = (source_time - a) / max(.0001, b - a)
            p = p * p * (3.0 - 2.0 * p)
            x1, y1 = _position_pixels(left["center"], width, height)
            x2, y2 = _position_pixels(right["center"], width, height)
            return x1 + (x2 - x1) * p, y1 + (y2 - y1) * p
    return _position_pixels(rows[-1]["center"], width, height)


def _draw_lock_effect(overlay: Image.Image, effect: dict[str, Any],
                      source_time: float, width: int, height: int) -> None:
    """Draw a restrained arena/object lock overlay; never a transition card."""
    start, end = float(effect.get("start", 0)), float(effect.get("end", 0))
    if not start <= source_time < end:
        return
    cx, cy = _lock_center(effect, source_time, width, height)
    raw_radius = float(effect.get("radius", .16))
    radius = raw_radius * min(width, height) if raw_radius <= 1.5 else raw_radius
    local = source_time - start
    pulse = 1.0 + .025 * math.sin(local * math.tau * 1.7)
    radius *= pulse
    color = tuple(int(value) for value in effect.get("color", [56, 215, 255]))
    line = max(3, round(height * float(effect.get("line_width", .0035))))
    layer = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    box = (round(cx - radius), round(cy - radius), round(cx + radius), round(cy + radius))
    angle = (local * float(effect.get("rotation_speed", 82))) % 360
    draw.ellipse(box, outline=(*color, 58), width=max(2, line // 2))
    for offset in (0, 180):
        draw.arc(box, start=angle + offset, end=angle + offset + 58,
                 fill=(*color, 235), width=line)
    bracket = radius * float(effect.get("bracket_length", .24))
    gap = radius * float(effect.get("bracket_gap", .88))
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        x, y = cx + sx * gap, cy + sy * gap
        draw.line((x, y, x - sx * bracket, y), fill=(*color, 220), width=line)
        draw.line((x, y, x, y - sy * bracket), fill=(*color, 220), width=line)
    glow = layer.filter(ImageFilter.GaussianBlur(max(3, round(height * .006))))
    glow.putalpha(glow.getchannel("A").point(lambda value: round(value * .52)))
    overlay.alpha_composite(glow)
    overlay.alpha_composite(layer)


def _alpha_matte(effect: dict[str, Any], rw: int, rh: int,
                 frame_box: tuple[int, int, int, int], frame_size: tuple[int, int]) -> Image.Image:
    """Load an editor-approved alpha matte as local bbox alpha.

    A full-frame matte is cropped to the tracked bbox; a local matte is resized.
    The source never supplies colour, so the effect cannot leak a hidden image.
    """
    raw = Image.open(str(effect["matte_path"]))
    source = raw.convert("RGBA")
    alpha = source.getchannel("A") if "A" in raw.getbands() else raw.convert("L")
    if source.size == frame_size:
        ix, iy, right, bottom = frame_box
        alpha = alpha.crop((ix, iy, right, bottom))
    if alpha.size != (rw, rh):
        alpha = alpha.resize((rw, rh), Image.Resampling.LANCZOS)
    return alpha


def _sequence_matte(effect: dict[str, Any], source_time: float,
                    rw: int, rh: int,
                    frame_box: tuple[int, int, int, int],
                    frame_size: tuple[int, int]) -> Image.Image:
    """Load a fail-closed, per-frame roto matte.

    Sequence mattes are the production path for a hand-held product, vehicle,
    person or other subject whose silhouette cannot be represented honestly by
    an ellipse or polygon.  Missing frames abort the render instead of silently
    falling back to a loose bounding box.
    """
    fps = float(effect["matte_sequence_fps"])
    sequence_start = float(effect.get("matte_sequence_start", effect.get("start", 0)))
    # A video frame owns the half-open interval [n/fps, (n+1)/fps).  Rounding
    # can request one frame beyond a complete matte sequence near effect-out.
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
    return _alpha_matte(local_effect, rw, rh, frame_box, frame_size)


def _verified_sheen_matte(effect: dict[str, Any], rw: int, rh: int,
                          frame_box: tuple[int, int, int, int],
                          frame_size: tuple[int, int],
                          source_time: float) -> Image.Image:
    shape = str(effect.get("shape", "ellipse"))
    if shape == "alpha":
        matte = _alpha_matte(effect, rw, rh, frame_box, frame_size)
    elif shape == "sequence":
        matte = _sequence_matte(effect, source_time, rw, rh, frame_box, frame_size)
    else:
        matte = Image.new("L", (rw, rh), 0)
        draw = ImageDraw.Draw(matte)
        inset = max(0.0, min(.35, float(effect.get("matte_inset", .025))))
        box = (round(rw * inset), round(rh * inset),
               round(rw * (1 - inset)), round(rh * (1 - inset)))
        if shape == "polygon":
            points = [(round(float(px) * rw), round(float(py) * rh))
                      for px, py in effect.get("polygon", [])]
            draw.polygon(points, fill=255)
        elif shape == "rectangle":
            radius = round(min(rw, rh) * float(effect.get("corner_radius", .08)))
            draw.rounded_rectangle(box, radius=radius, fill=255)
        else:
            draw.ellipse(box, fill=255)
    feather = max(1, round(min(rw, rh) * float(effect.get("matte_feather", .018))))
    return matte.filter(ImageFilter.GaussianBlur(feather))


def _draw_mask_sheen(overlay: Image.Image, effect: dict[str, Any],
                     source_time: float, width: int, height: int) -> None:
    """Sweep a feathered diagonal highlight inside a verified subject matte.

    This is a tracked object-treatment overlay, not a flash transition.  The
    default ellipse is useful for circular products such as battle tops;
    ``polygon`` supports an editor-verified local matte for irregular subjects.
    """
    start, end = float(effect.get("start", 0)), float(effect.get("end", 0))
    if not start <= source_time < end:
        return
    x, y, w, h = _keyframed_bbox(effect, source_time, width, height)
    ix, iy = max(0, round(x)), max(0, round(y))
    rw = max(4, min(width - ix, round(w)))
    rh = max(4, min(height - iy, round(h)))
    if rw < 4 or rh < 4:
        return

    frame_box = (ix, iy, ix + rw, iy + rh)
    matte = _verified_sheen_matte(effect, rw, rh, frame_box, (width, height), source_time)

    material = SHEEN_MATERIALS[str(effect.get("material_profile", "generic_product"))]

    progress = (source_time - start) / max(.001, end - start)
    yy, xx = np.mgrid[0:rh, 0:rw].astype(np.float32)
    angle = math.radians(float(effect.get("angle", -28.0)))
    projection = xx * math.cos(angle) + yy * math.sin(angle)
    p_min, p_max = float(projection.min()), float(projection.max())
    travel_pad = (p_max - p_min) * .20
    center = (p_min - travel_pad) + progress * ((p_max - p_min) + travel_pad * 2)
    sigma = max(2.0, min(rw, rh) * float(effect.get("band_width", material["band_width"])) * .38)
    band = np.exp(-.5 * ((projection - center) / sigma) ** 2)
    secondary = float(effect.get("secondary", material["secondary"]))
    secondary_center = center - sigma * 2.15
    band += secondary * np.exp(-.5 * ((projection - secondary_center) / (sigma * .52)) ** 2)
    matte_alpha = np.asarray(matte, dtype=np.float32) / 255.0

    # Premium subject reveal: the photographed object begins fully black and
    # the same diagonal frontier restores its original colour.  The blackout
    # is clipped by the exact same editor-approved matte as the sheen, so this
    # can never darken a hand, caption, arena or background.  This is an object
    # treatment, not a typography effect and not a full-frame transition.
    reveal_mode = str(effect.get("reveal_mode", "sheen_only"))
    if reveal_mode == "black_to_color":
        reveal_softness = max(.08, min(1.2, float(effect.get("reveal_softness", .42))))
        edge_sigma = max(1.0, sigma * reveal_softness)
        exponent = np.clip((projection - center) / edge_sigma, -24.0, 24.0)
        revealed = 1.0 / (1.0 + np.exp(exponent))
        blackout_opacity = max(0.0, min(1.0, float(effect.get("blackout_opacity", 1.0))))
        blackout_alpha = np.clip(
            (1.0 - revealed) * matte_alpha * blackout_opacity * 255.0,
            0, 255,
        ).astype(np.uint8)
        blackout = Image.new("RGBA", (rw, rh), (0, 0, 0, 0))
        blackout.putalpha(Image.fromarray(blackout_alpha))
        overlay.alpha_composite(blackout, (ix, iy))

    alpha = band * matte_alpha
    opacity = max(0.0, min(1.0, float(effect.get("opacity", material["opacity"]))))
    core = max(0.01, min(1.0, float(effect.get("core", material["core"]))))
    alpha = np.clip(alpha * opacity * core * 255.0, 0, 255).astype(np.uint8)
    color = tuple(int(v) for v in effect.get("color", [255, 255, 255]))
    local = Image.new("RGBA", (rw, rh), (*color, 0))
    local.putalpha(Image.fromarray(alpha))

    # Subject-only contrast shoulders make the bright sweep readable on white
    # or low-contrast products.  They remain narrow and are clipped by the same
    # verified matte, so hands, arena and background cannot be dimmed.
    contrast = max(0.0, min(.45, float(effect.get("contrast", material["contrast"]))))
    if contrast:
        shoulder_distance = sigma * float(effect.get("shoulder_distance", 1.42))
        shoulder_sigma = sigma * float(effect.get("shoulder_width", .72))
        shoulder = (
            np.exp(-.5 * ((projection - (center - shoulder_distance)) / shoulder_sigma) ** 2)
            + np.exp(-.5 * ((projection - (center + shoulder_distance)) / shoulder_sigma) ** 2)
        )
        shoulder *= np.clip(1.0 - band * .82, 0.0, 1.0)
        shadow_alpha = np.clip(shoulder * matte_alpha * contrast * 255.0, 0, 255).astype(np.uint8)
        shadow = Image.new("RGBA", (rw, rh), (4, 8, 14, 0))
        shadow.putalpha(Image.fromarray(shadow_alpha))
        overlay.alpha_composite(shadow, (ix, iy))

    glow_radius = max(1, round(min(rw, rh) * float(effect.get("glow", material["glow"]))))
    glow = local.filter(ImageFilter.GaussianBlur(glow_radius))
    # Blur expands beyond its source alpha by design. Re-clip that expanded
    # halo to the verified matte so a product sheen can never light the hand,
    # background, or a neighbouring object outside the approved subject.
    glow_alpha = np.asarray(glow.getchannel("A"), dtype=np.float32)
    glow_alpha = np.clip(glow_alpha * matte_alpha * .45, 0, 255).astype(np.uint8)
    glow.putalpha(Image.fromarray(glow_alpha))
    overlay.alpha_composite(glow, (ix, iy))
    overlay.alpha_composite(local, (ix, iy))


def _overlay_frame(frame: np.ndarray, overlay: Image.Image) -> np.ndarray:
    background = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
    background.alpha_composite(overlay)
    return cv2.cvtColor(np.asarray(background.convert("RGB")), cv2.COLOR_RGB2BGR)


def _write_contact_sheet(frames: list[np.ndarray], output: Path, columns: int = 3) -> None:
    if not frames:
        return
    thumbs = []
    for frame in frames:
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        image.thumbnail((480, 270), Image.Resampling.LANCZOS)
        thumbs.append(image)
    rows = math.ceil(len(thumbs) / columns)
    sheet = Image.new("RGB", (480 * columns, 270 * rows), (13, 17, 25))
    for index, image in enumerate(thumbs):
        sheet.paste(image, ((index % columns) * 480, (index // columns) * 270))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def _prepare_tracking_source(source: Path, start: float, duration: float,
                             temp_dir: Path) -> tuple[Path, dict[str, Any]]:
    """Create an upright, display-referred, high-quality tracking segment.

    iPhone portrait MOV files commonly store landscape pixels plus rotation
    metadata and HLG transfer characteristics.  OpenCV ignores both.  Feeding
    those bytes directly to a tracker makes bbox coordinates, colour and final
    composite quality wrong.  FFmpeg applies the display rotation, converts
    HDR to Rec.709 when required, and writes a short-lived 10-bit ProRes segment
    so the overlay is composited only once into the delivery encode.
    """
    analysis = analyze_media(str(source))
    if analysis.get("unknown_log"):
        raise RuntimeError("unknown Log source requires an explicit input transform: " + str(source))
    filters: list[str] = []
    if analysis.get("is_hdr"):
        filters.append(
            "zscale=t=linear:npl=100,format=gbrpf32le,"
            "tonemap=hable:desat=0,zscale=p=bt709:t=bt709:m=bt709:r=tv"
        )
    filters.extend(("setsar=1", "format=yuv422p10le"))
    prepared = temp_dir / "prepared_tracking_source.mov"
    command = [
        "ffmpeg", "-v", "error", "-y", "-i", str(source),
        "-ss", "%.6f" % start, "-t", "%.6f" % duration,
        "-vf", ",".join(filters), "-an", "-c:v", "prores_ks",
        "-profile:v", "3", "-pix_fmt", "yuv422p10le",
        "-metadata:s:v:0", "rotate=0", str(prepared),
    ]
    run = subprocess.run(command, capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    if run.returncode:
        raise RuntimeError("tracking source preparation failed: " + run.stderr[-700:])
    return prepared, {
        "display_rotation_applied": True,
        "input_transfer": analysis.get("color_transfer", "unknown"),
        "hdr_to_rec709": bool(analysis.get("is_hdr")),
        "intermediate": "prores_ks_profile_3_yuv422p10le",
        "graphics_stage": "after_input_transform_before_delivery_encode",
    }


def _composite_overlay(base_video: Path, overlay_video: Path, source: Path,
                       start: float, duration: float, output: Path) -> None:
    """Composite the transparent overlay once and restore source audio."""
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-v", "error", "-y", "-i", str(base_video),
        "-i", str(overlay_video), "-ss", "%.6f" % start,
        "-t", "%.6f" % duration, "-i", str(source),
        "-filter_complex", "[0:v][1:v]overlay=shortest=1:format=auto,format=yuv420p[v]",
        "-map", "[v]", "-map", "2:a:0?", "-c:v", "libx264",
        "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        "-shortest", str(output),
    ]
    run = subprocess.run(command, capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    if run.returncode:
        raise RuntimeError("tracked overlay composite failed: " + run.stderr[-700:])


def _mux_audio(video_only: Path, source: Path, start: float, duration: float, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-v", "error", "-y", "-i", str(video_only),
        "-ss", "%.6f" % start, "-t", "%.6f" % duration, "-i", str(source),
        "-map", "0:v:0", "-map", "1:a:0?", "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError("ffmpeg mux failed: " + result.stderr[-700:])


def _start_alpha_writer(path: Path, width: int, height: int, fps: float):
    path.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.Popen([
        "ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba",
        "-s", "%dx%d" % (width, height), "-r", "%.6f" % fps, "-i", "-",
        "-an", "-c:v", "qtrle", "-pix_fmt", "argb", str(path),
    ], stdin=subprocess.PIPE, stderr=subprocess.PIPE)


def _close_alpha_writer(process) -> None:
    if not process or not process.stdin:
        return
    process.stdin.close()
    stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    code = process.wait()
    if code:
        raise RuntimeError("alpha render failed: " + stderr[-700:])


def _render_frame_range(cap, writer, alpha_proc, runtimes, spec, *,
                        width: int, height: int, fps: float,
                        start_frame: int, end_frame: int,
                        source_time_offset: float = 0.0) -> tuple[int, list[np.ndarray]]:
    qa_frames: list[np.ndarray] = []
    sample_every = max(1, (end_frame - start_frame) // 8)
    written = 0
    for absolute_frame in range(start_frame, end_frame):
        ok, frame = cap.read()
        if not ok:
            break
        source_time = source_time_offset + (absolute_frame - start_frame) / fps
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        for runtime in runtimes:
            if not runtime.active(source_time):
                continue
            first = False
            if not runtime.initialized:
                runtime.initialize(frame)
                first = True
            status, confidence = runtime.update(frame, source_time, first_frame=first)
            runtime.draw(overlay, source_time, confidence)
            box = runtime.smooth_box
            runtime.records.append({
                "frame": round(source_time * fps), "time": round(source_time, 4),
                "status": status, "confidence": round(confidence, 3),
                "bbox": [round(value, 2) for value in box] if box else None,
            })
        for effect in spec.get("lock_effects", []):
            _draw_lock_effect(overlay, effect, source_time, width, height)
        for effect in spec.get("mask_sheens", []):
            _draw_mask_sheen(overlay, effect, source_time, width, height)
        hud = spec.get("hud")
        if hud and float(hud.get("start", start_frame / fps)) <= source_time < \
                float(hud.get("end", end_frame / fps)):
            overlay.alpha_composite(render_challenge_hud((width, height), hud, source_time))
        composed = _overlay_frame(frame, overlay)
        if writer is not None:
            writer.write(composed)
        if alpha_proc and alpha_proc.stdin:
            alpha_proc.stdin.write(np.asarray(overlay, dtype=np.uint8).tobytes())
        if written % sample_every == 0:
            qa_frames.append(composed.copy())
        written += 1
    return written, qa_frames


def _build_render_report(source: Path, output: Path, alpha_output: Path | None,
                         spec: dict[str, Any], runtimes, track_records,
                         width: int, height: int, fps: float, written: int,
                         source_preparation: dict[str, Any] | None = None) -> dict[str, Any]:
    total_updates = sum(len(records) for records in track_records.values())
    lost_updates = sum(1 for records in track_records.values() for item in records if item["status"] != "tracked")
    lost_ratio = lost_updates / max(1, total_updates)
    modes = {str(runtime.config.get("tracking_mode", "csrt")) for runtime in runtimes}
    if modes == {"keyframes"}:
        engine = "verified_keyframes"
    elif "keyframes" in modes:
        engine = "hybrid_csrt_keyframes"
    else:
        engine = "opencv_csrt"
    return {
        "status": "GREEN" if total_updates == 0 or lost_ratio <= .12 else "REVIEW",
        "classification": "graphic_overlay", "is_transition": False,
        "source": str(source), "output": str(output),
        "alpha_output": str(alpha_output) if alpha_output else None,
        "resolution": [width, height], "fps": fps,
        "frames": written, "duration": round(written / fps, 4),
        "source_preparation": source_preparation or {},
        "delivery_encode": {
            "codec": "libx264", "crf": 16, "preset": "slow",
            "overlay_composites": 1,
        },
        "tracking": {
            "engine": engine, "tracks": len(runtimes),
            "updates": total_updates, "lost_or_held": lost_updates,
            "lost_ratio": round(lost_ratio, 4),
            "failure_policy": "hold_last_valid_for_limited_frames_then_hide; never_guess",
        },
        "hud": {
            "enabled": bool(spec.get("hud")), "mode": (spec.get("hud") or {}).get("mode"),
            "meaning": "stateful challenge record, not decoration or transition",
        },
        "subject_locks": {
            "count": len(spec.get("lock_effects", [])),
            "meaning": "verified arena/object attention lock, never a transition",
        },
        "mask_sheens": {
            "count": len(spec.get("mask_sheens", [])),
            "meaning": "high-contrast diagonal material highlight or black-to-colour reveal clipped to a verified photographed subject object; never typography or a full-frame flash",
            "target_kind": "subject_object_only",
            "typography_target_allowed": False,
            "matte_clip_enforced": True,
            "full_frame_flash_possible": False,
            "material_profiles": sorted({
                str(row.get("material_profile", "generic_product"))
                for row in spec.get("mask_sheens", [])
            }),
            "matte_sources": sorted({
                str(row.get("shape", "ellipse"))
                for row in spec.get("mask_sheens", [])
            }),
            "reveal_modes": sorted({
                str(row.get("reveal_mode", "sheen_only"))
                for row in spec.get("mask_sheens", [])
            }),
            "qa": "review start, peak and end frame; reject edge leak, drift, occlusion error or subject clipping",
        },
    }


def render_spec(spec: dict[str, Any], output: str | Path, *,
                alpha_output: str | Path | None = None,
                track_output: str | Path | None = None,
                qa_sheet: str | Path | None = None) -> dict[str, Any]:
    errors = validate_spec(spec)
    if errors:
        raise ValueError("invalid tracked-graphics spec: " + "; ".join(errors))
    source = Path(spec["video"]).resolve()
    output = Path(output).resolve()
    start, end = float(spec.get("start", 0)), float(spec["end"])
    duration = end - start
    temp_dir = Path(tempfile.mkdtemp(prefix="tracked-graphics-"))
    prepared_source, source_preparation = _prepare_tracking_source(
        source, start, duration, temp_dir)
    cap = cv2.VideoCapture(str(prepared_source))
    if not cap.isOpened():
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError("could not open prepared tracking source")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    start_frame, end_frame = 0, round(duration * fps)
    label_configs = []
    for item in spec.get("tracked_labels", []):
        config = dict(item)
        config.setdefault("start", start)
        config.setdefault("end", end)
        label_configs.append(config)
    runtimes = [TrackRuntime(config, width, height) for config in label_configs]
    track_records: dict[str, list[dict[str, Any]]] = {
        str(runtime.config.get("id", "track-%d" % index)): runtime.records
        for index, runtime in enumerate(runtimes)
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    requested_alpha = Path(alpha_output).resolve() if alpha_output else None
    overlay_video = requested_alpha or (temp_dir / "tracked_overlay.mov")
    alpha_proc = _start_alpha_writer(overlay_video, width, height, fps)

    try:
        written, qa_frames = _render_frame_range(
            cap, None, alpha_proc, runtimes, spec,
            width=width, height=height, fps=fps,
            start_frame=start_frame, end_frame=end_frame,
            source_time_offset=start,
        )
    finally:
        cap.release()
        _close_alpha_writer(alpha_proc)

    if written < 1:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError("no frames were rendered")
    rendered_duration = written / fps
    _composite_overlay(prepared_source, overlay_video, source, start,
                       rendered_duration, output)

    report = _build_render_report(
        source, output, requested_alpha, spec, runtimes,
        track_records, width, height, fps, written,
        source_preparation,
    )
    if track_output:
        track_output = Path(track_output).resolve()
        track_output.parent.mkdir(parents=True, exist_ok=True)
        track_output.write_text(json.dumps({"report": report, "tracks": track_records}, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")
        report["track_output"] = str(track_output)
    if qa_sheet:
        qa_sheet = Path(qa_sheet).resolve()
        _write_contact_sheet(qa_frames, qa_sheet)
        report["qa_sheet"] = str(qa_sheet)
    shutil.rmtree(temp_dir, ignore_errors=True)
    return report


def _make_demo_source(path: Path, *, fps: int = 30, duration: float = 2.8) -> list[tuple[float, float]]:
    width, height = 640, 360
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    truth = []
    for frame_index in range(round(fps * duration)):
        frame = np.full((height, width, 3), (44, 35, 29), dtype=np.uint8)
        for x in range(0, width, 40):
            cv2.line(frame, (x, 0), (x, height), (55, 47, 42), 1)
        for y in range(0, height, 40):
            cv2.line(frame, (0, y), (width, y), (55, 47, 42), 1)
        x = 62 + frame_index * 3.0
        y = 190 + math.sin(frame_index * .10) * 22
        truth.append((x + 48, y + 32))
        cv2.rectangle(frame, (round(x), round(y)), (round(x + 96), round(y + 64)), (35, 80, 224), -1)
        cv2.rectangle(frame, (round(x + 5), round(y + 5)), (round(x + 91), round(y + 59)), (235, 185, 43), 4)
        cv2.line(frame, (round(x + 10), round(y + 10)), (round(x + 86), round(y + 54)), (255, 255, 255), 3)
        cv2.line(frame, (round(x + 86), round(y + 10)), (round(x + 10), round(y + 54)), (255, 255, 255), 3)
        writer.write(frame)
    writer.release()
    return truth


def build_typography_catalog(path: str | Path) -> Path:
    """Render a review sheet proving CJK, Latin, numeric and mixed-script support."""
    samples = [
        ("挑戰成功", "neon_value_green"),
        ("LEVEL UP", "neon_value_cyan"),
        ("$300,000", "price_white"),
        ("AI 挑戰 #01", "impact_gold"),
    ]
    tile_w, tile_h = 760, 300
    sheet = Image.new("RGBA", (tile_w * 2, tile_h * 2), (10, 13, 20, 255))
    for index, (text, profile) in enumerate(samples):
        tile = Image.new("RGBA", (tile_w, tile_h), (15, 20, 31, 255))
        plate = render_text_plate(text, profile, 118, max_width=tile_w - 50)
        tile.alpha_composite(plate, ((tile_w - plate.width) // 2, (tile_h - plate.height) // 2))
        ImageDraw.Draw(tile).text((18, 14), profile, font=_font(profile, 20), fill=(151, 169, 195, 255))
        sheet.alpha_composite(tile, ((index % 2) * tile_w, (index // 2) * tile_h))
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(path, quality=94)
    return path


def build_demo(out_dir: str | Path) -> dict[str, Any]:
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    source = out_dir / "source.mp4"
    truth = _make_demo_source(source)
    spec = {
        "video": str(source), "start": 0, "end": 2.8,
        "tracked_labels": [{
            "id": "demo-object", "text": "$300,000 / 挑戰成功", "profile": "neon_value_green",
            "initial_bbox": [62, 190, 96, 64], "start": 0, "end": 2.8,
            "style": "telemetry_callout", "meaning": "synthetic tracked value proof",
            "panel_offset": [-.16, -.15], "pointer_target": [.5, .5],
            "anchor": "top", "evidence": "synthetic demo ground truth",
        }],
        "mask_sheens": [{
            "id": "demo-sheen", "start": .6, "end": 1.15,
            "initial_bbox": [62, 190, 96, 64],
            "keyframes": [
                {"time": .6, "bbox": [116, 188, 96, 64]},
                {"time": 1.15, "bbox": [166, 172, 96, 64]},
            ],
            "shape": "rectangle", "angle": -28, "band_width": .13,
            "target_kind": "subject_object", "contrast": .18,
            "reveal_mode": "black_to_color", "blackout_opacity": 1.0,
            "subject_class": "product", "material_profile": "plastic_product",
            "evidence": "synthetic demo object matte",
        }],
        "hud": {
            "mode": "ladder", "active_index": 0,
            "events": [{"time": .9, "active_index": 1}, {"time": 1.8, "active_index": 2}],
            "items": [
                {"label": "$1", "evidence": "synthetic demo", "accent": [84, 211, 255]},
                {"label": "$50K", "evidence": "synthetic demo", "accent": [255, 197, 61]},
                {"label": "$300K", "evidence": "synthetic demo", "accent": [105, 255, 113]},
            ],
        },
    }
    spec_path = out_dir / "spec.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = render_spec(
        spec, out_dir / "tracked_graphics_demo.mp4",
        alpha_output=out_dir / "tracked_graphics_overlay.mov",
        track_output=out_dir / "tracking.json",
        qa_sheet=out_dir / "contact_sheet.jpg",
    )
    report["typography_catalog"] = str(build_typography_catalog(out_dir / "typography_catalog.jpg"))
    tracking = json.loads((out_dir / "tracking.json").read_text(encoding="utf-8"))
    records = tracking["tracks"]["demo-object"]
    errors = []
    for index, record in enumerate(records):
        if not record["bbox"]:
            continue
        x, y, w, h = record["bbox"]
        truth_x, truth_y = truth[min(index, len(truth) - 1)]
        errors.append(math.hypot(x + w / 2 - truth_x, y + h / 2 - truth_y))
    report["demo_mean_track_error_px"] = round(sum(errors) / max(1, len(errors)), 3)
    report_path = out_dir / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["report_path"] = str(report_path)
    return report


def self_test() -> None:
    assert not validate_spec({"video": "missing.mp4", "start": 0, "end": 1}) == []
    invalid = {
        "video": __file__, "start": 0, "end": 1,
        "tracked_labels": [{"text": "$100", "initial_bbox": [0, 0, 10, 10], "start": 0, "end": 1}],
    }
    assert any("requires evidence" in error for error in validate_spec(invalid))
    with tempfile.TemporaryDirectory(prefix="tracked-graphics-selftest-") as temp:
        report = build_demo(temp)
        assert report["classification"] == "graphic_overlay" and report["is_transition"] is False
        assert report["mask_sheens"]["matte_clip_enforced"] is True
        assert report["mask_sheens"]["full_frame_flash_possible"] is False
        assert report["mask_sheens"]["typography_target_allowed"] is False
        assert report["mask_sheens"]["reveal_modes"] == ["black_to_color"]
        assert report["tracking"]["lost_ratio"] < .15
        assert report["demo_mean_track_error_px"] < 24, report
        for name in ("tracked_graphics_demo.mp4", "tracked_graphics_overlay.mov",
                     "tracking.json", "contact_sheet.jpg", "typography_catalog.jpg"):
            assert (Path(temp) / name).stat().st_size > 1000
    invalid_text_sheen = {
        "video": __file__, "start": 0, "end": .5,
        "mask_sheens": [{
            "start": 0, "end": .4, "initial_bbox": [0, 0, 40, 40],
            "shape": "rectangle", "subject_class": "typography",
            "target_kind": "typography", "evidence": "negative fixture",
        }],
    }
    assert any("never text" in error or "belongs to text effects" in error
               for error in validate_spec(invalid_text_sheen))
    print("tracked_graphics self-test GREEN")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render tracked typography and challenge-ledger HUD overlays")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("spec")
    render = sub.add_parser("render")
    render.add_argument("spec")
    render.add_argument("--output", required=True)
    render.add_argument("--alpha-output", default="")
    render.add_argument("--track-output", default="")
    render.add_argument("--qa-sheet", default="")
    demo = sub.add_parser("demo")
    demo.add_argument("--out-dir", required=True)
    sub.add_parser("selftest")
    args = parser.parse_args()
    if args.command == "selftest":
        self_test()
        return 0
    if args.command == "demo":
        print(json.dumps(build_demo(args.out_dir), ensure_ascii=False, indent=2))
        return 0
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    errors = validate_spec(spec)
    if args.command == "validate":
        print(json.dumps({"status": "GREEN" if not errors else "RED", "errors": errors},
                         ensure_ascii=False, indent=2))
        return 0 if not errors else 1
    report = render_spec(
        spec, args.output,
        alpha_output=args.alpha_output or None,
        track_output=args.track_output or None,
        qa_sheet=args.qa_sheet or None,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
