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
        self.base_plate = render_text_plate(
            text, profile, round(self.frame_height * font_scale),
            max_width=round(self.frame_width * float(self.config.get("max_width", .64))),
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
        anchor = str(self.config.get("anchor", "top"))
        gap = round(self.frame_height * float(self.config.get("gap", .018)))
        if anchor == "bottom":
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

        pointer = self.config.get("pointer")
        if pointer == "arrow":
            draw = ImageDraw.Draw(overlay, "RGBA")
            color = tuple(self.config.get("pointer_color", [255, 38, 45]))
            start_pt = (px + plate.width // 2, py + plate.height - max(4, gap // 3))
            target = self.config.get("pointer_target", [.5, .32])
            tx, ty = float(target[0]), float(target[1])
            end_pt = (round(x + w * tx), round(y + h * ty))
            thickness = max(5, round(self.frame_height * .008))
            draw.line((start_pt, end_pt), fill=(*color, 255), width=thickness)
            angle = math.atan2(end_pt[1] - start_pt[1], end_pt[0] - start_pt[0])
            head = max(12, round(self.frame_height * .025))
            points = [end_pt]
            for delta in (2.55, -2.55):
                points.append((round(end_pt[0] + math.cos(angle + delta) * head),
                               round(end_pt[1] + math.sin(angle + delta) * head)))
            draw.polygon(points, fill=(*color, 255))
        overlay.alpha_composite(plate, (px, py))


def validate_spec(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    source = Path(str(spec.get("video", "")))
    if not source.is_file():
        errors.append("video does not exist")
    start = float(spec.get("start", 0))
    end = float(spec.get("end", start))
    if end <= start:
        errors.append("end must exceed start")
    for index, label in enumerate(spec.get("tracked_labels", [])):
        prefix = "tracked_labels[%d]" % index
        if not str(label.get("text", "")).strip():
            errors.append(prefix + " text is empty")
        if label.get("profile", "neon_value_green") not in TEXT_PROFILES:
            errors.append(prefix + " has unknown profile")
        if not isinstance(label.get("initial_bbox"), list) or len(label.get("initial_bbox", [])) != 4:
            errors.append(prefix + " initial_bbox must be a four-value list")
        mode = str(label.get("tracking_mode", "csrt"))
        if mode not in {"csrt", "keyframes"}:
            errors.append(prefix + " tracking_mode must be csrt or keyframes")
        if mode == "keyframes":
            keyframes = label.get("keyframes") or []
            if not keyframes:
                errors.append(prefix + " keyframes mode requires keyframes")
            previous_time = -float("inf")
            for key_index, row in enumerate(keyframes):
                if not isinstance(row.get("bbox"), list) or len(row.get("bbox", [])) != 4:
                    errors.append(prefix + ".keyframes[%d] bbox must be a four-value list" % key_index)
                current_time = float(row.get("time", -1))
                if current_time < previous_time:
                    errors.append(prefix + " keyframes must be time ordered")
                previous_time = current_time
        if float(label.get("end", end)) <= float(label.get("start", start)):
            errors.append(prefix + " end must exceed start")
        if CURRENCY_RE.search(str(label.get("text", ""))) and not str(label.get("evidence", "")).strip():
            errors.append(prefix + " currency/value text requires evidence")
    hud = spec.get("hud")
    if hud:
        if hud.get("mode", "current_badge") not in {"current_badge", "ladder"}:
            errors.append("hud.mode must be current_badge or ladder")
        if not hud.get("items"):
            errors.append("hud.items must not be empty")
        for index, item in enumerate(hud.get("items", [])):
            if not str(item.get("label", "")).strip():
                errors.append("hud.items[%d] label is empty" % index)
            if CURRENCY_RE.search(str(item.get("label", ""))) and not str(item.get("evidence", "")).strip():
                errors.append("hud.items[%d] currency/value text requires evidence" % index)
    for index, effect in enumerate(spec.get("lock_effects", [])):
        prefix = "lock_effects[%d]" % index
        if float(effect.get("end", end)) <= float(effect.get("start", start)):
            errors.append(prefix + " end must exceed start")
        center = effect.get("center", [.5, .53])
        if not isinstance(center, list) or len(center) != 2:
            errors.append(prefix + " center must be a two-value list")
        if float(effect.get("radius", .16)) <= 0:
            errors.append(prefix + " radius must be positive")
    for index, effect in enumerate(spec.get("mask_sheens", [])):
        prefix = "mask_sheens[%d]" % index
        if float(effect.get("end", end)) <= float(effect.get("start", start)):
            errors.append(prefix + " end must exceed start")
        if not isinstance(effect.get("initial_bbox"), list) or len(effect.get("initial_bbox", [])) != 4:
            errors.append(prefix + " initial_bbox must be a four-value list")
        if effect.get("shape", "ellipse") not in {"ellipse", "rectangle", "polygon"}:
            errors.append(prefix + " shape must be ellipse, rectangle or polygon")
        if effect.get("shape") == "polygon" and len(effect.get("polygon") or []) < 3:
            errors.append(prefix + " polygon shape requires at least three points")
        if float(effect.get("band_width", .16)) <= 0:
            errors.append(prefix + " band_width must be positive")
        if not str(effect.get("evidence", "")).strip():
            errors.append(prefix + " requires evidence for the subject matte")
    return errors


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

    matte = Image.new("L", (rw, rh), 0)
    draw = ImageDraw.Draw(matte)
    shape = str(effect.get("shape", "ellipse"))
    inset = max(0.0, min(.35, float(effect.get("matte_inset", .025))))
    box = (round(rw * inset), round(rh * inset),
           round(rw * (1 - inset)), round(rh * (1 - inset)))
    if shape == "polygon":
        points = []
        for px, py in effect.get("polygon", []):
            points.append((round(float(px) * rw), round(float(py) * rh)))
        draw.polygon(points, fill=255)
    elif shape == "rectangle":
        radius = round(min(rw, rh) * float(effect.get("corner_radius", .08)))
        draw.rounded_rectangle(box, radius=radius, fill=255)
    else:
        draw.ellipse(box, fill=255)
    feather = max(1, round(min(rw, rh) * float(effect.get("matte_feather", .018))))
    matte = matte.filter(ImageFilter.GaussianBlur(feather))

    progress = (source_time - start) / max(.001, end - start)
    yy, xx = np.mgrid[0:rh, 0:rw].astype(np.float32)
    angle = math.radians(float(effect.get("angle", -28.0)))
    projection = xx * math.cos(angle) + yy * math.sin(angle)
    p_min, p_max = float(projection.min()), float(projection.max())
    travel_pad = (p_max - p_min) * .20
    center = (p_min - travel_pad) + progress * ((p_max - p_min) + travel_pad * 2)
    sigma = max(2.0, min(rw, rh) * float(effect.get("band_width", .16)) * .38)
    band = np.exp(-.5 * ((projection - center) / sigma) ** 2)
    alpha = band * (np.asarray(matte, dtype=np.float32) / 255.0)
    opacity = max(0.0, min(1.0, float(effect.get("opacity", .68))))
    alpha = np.clip(alpha * opacity * 255.0, 0, 255).astype(np.uint8)
    color = tuple(int(v) for v in effect.get("color", [255, 255, 255]))
    local = Image.new("RGBA", (rw, rh), (*color, 0))
    local.putalpha(Image.fromarray(alpha))

    glow_radius = max(1, round(min(rw, rh) * float(effect.get("glow", .022))))
    glow = local.filter(ImageFilter.GaussianBlur(glow_radius))
    glow.putalpha(glow.getchannel("A").point(lambda value: round(value * .45)))
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
                        start_frame: int, end_frame: int) -> tuple[int, list[np.ndarray]]:
    qa_frames: list[np.ndarray] = []
    sample_every = max(1, (end_frame - start_frame) // 8)
    written = 0
    for absolute_frame in range(start_frame, end_frame):
        ok, frame = cap.read()
        if not ok:
            break
        source_time = absolute_frame / fps
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
                "frame": absolute_frame, "time": round(source_time, 4),
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
        writer.write(composed)
        if alpha_proc and alpha_proc.stdin:
            alpha_proc.stdin.write(np.asarray(overlay, dtype=np.uint8).tobytes())
        if written % sample_every == 0:
            qa_frames.append(composed.copy())
        written += 1
    return written, qa_frames


def _build_render_report(source: Path, output: Path, alpha_output: Path | None,
                         spec: dict[str, Any], runtimes, track_records,
                         width: int, height: int, fps: float, written: int) -> dict[str, Any]:
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
            "meaning": "diagonal highlight clipped to a verified subject matte; never a full-frame flash",
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
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise RuntimeError("could not open source video")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    start, end = float(spec.get("start", 0)), float(spec["end"])
    start_frame, end_frame = round(start * fps), round(end * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
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
    temp_dir = Path(tempfile.mkdtemp(prefix="tracked-graphics-"))
    video_only = temp_dir / "video_only.mp4"
    writer = cv2.VideoWriter(str(video_only), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError("could not create temporary video")

    alpha_proc = None
    if alpha_output:
        alpha_output = Path(alpha_output).resolve()
        alpha_proc = _start_alpha_writer(alpha_output, width, height, fps)

    try:
        written, qa_frames = _render_frame_range(
            cap, writer, alpha_proc, runtimes, spec,
            width=width, height=height, fps=fps,
            start_frame=start_frame, end_frame=end_frame,
        )
    finally:
        cap.release()
        writer.release()
        _close_alpha_writer(alpha_proc)

    if written < 1:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError("no frames were rendered")
    duration = written / fps
    _mux_audio(video_only, source, start, duration, output)
    shutil.rmtree(temp_dir, ignore_errors=True)

    report = _build_render_report(
        source, output, Path(alpha_output) if alpha_output else None, spec, runtimes,
        track_records, width, height, fps, written,
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
            "anchor": "top", "evidence": "synthetic demo ground truth",
        }],
        "mask_sheens": [{
            "id": "demo-sheen", "start": .6, "end": 1.15,
            "initial_bbox": [62, 190, 96, 64],
            "keyframes": [
                {"time": .6, "bbox": [116, 188, 96, 64]},
                {"time": 1.15, "bbox": [166, 172, 96, 64]},
            ],
            "shape": "rectangle", "angle": -28, "band_width": .18,
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
        assert report["tracking"]["lost_ratio"] < .15
        assert report["demo_mean_track_error_px"] < 24, report
        for name in ("tracked_graphics_demo.mp4", "tracked_graphics_overlay.mov",
                     "tracking.json", "contact_sheet.jpg", "typography_catalog.jpg"):
            assert (Path(temp) / name).stat().st_size > 1000
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
